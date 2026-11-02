"""Local speech input: microphone via sounddevice, transcription via faster-whisper.

Push-to-talk: record() starts at once and stops by itself after a short pause.
The Whisper model is downloaded once from Hugging Face, then runs offline on the CPU.
"""
import os
import threading

RATE = 16000
BLOCK = 480  # 30 ms
MODELS = ("base", "small", "medium")
LANGUAGES = ("de", "en")
PROMPT = "Pixel Buddy. Play, Pause, Spotify, Next song, Resume. Nächster Song, Musik."


class ListenError(Exception):
    pass


def find_speech(levels, block_ms=30, calibrate_ms=300, end_silence_ms=900,
                no_speech_ms=7000, max_ms=15000, min_level=0.01):
    """Decide from block RMS levels when speech started/ended.

    Returns ("more", None) while recording should continue, ("done", n) with the
    number of blocks to keep, or ("silent", None) if nobody spoke.
    Pure function so the endpointing can be tested without a microphone.
    """
    calibrate = max(1, calibrate_ms // block_ms)
    if len(levels) < calibrate:
        return "more", None
    floor = sorted(levels[:calibrate])[calibrate // 2]
    threshold = max(min_level, floor * 3)
    loud = [level > threshold for level in levels]
    start = next((i for i in range(len(loud) - 2) if loud[i] and loud[i + 1] and loud[i + 2]), None)
    if start is None:
        if len(levels) * block_ms >= no_speech_ms:
            return "silent", None
        return "more", None
    last = max(i for i, value in enumerate(loud) if value)
    if (len(levels) - 1 - last) * block_ms >= end_silence_ms or len(levels) * block_ms >= max_ms:
        return "done", len(levels)
    return "more", None


class Listener:
    def __init__(self, model="base", log=print):
        if model not in MODELS:
            raise ListenError("Unbekanntes Whisper-Modell: " + model)
        try:
            import numpy
            import sounddevice
        except ImportError as exc:
            raise ListenError("Pakete fehlen: python -m pip install faster-whisper sounddevice") from exc
        try:
            sounddevice.check_input_settings(samplerate=RATE, channels=1, dtype="float32")
        except Exception as exc:  # PortAudio raises several types
            raise ListenError("Kein nutzbares Mikrofon: {}".format(exc)) from exc
        self.np = numpy
        self.sd = sounddevice
        self.log = log
        self.model_name = model
        self.model = None
        self.error = None
        self.loaded = threading.Event()
        threading.Thread(target=self._load, name="whisper-load", daemon=True).start()

    def _load(self):
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
        try:
            from faster_whisper import WhisperModel
            self.model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
        except Exception as exc:  # download, disk or runtime problems
            self.error = "Whisper-Modell nicht ladbar: {}".format(exc)
        self.loaded.set()

    def wait_model(self):
        if not self.loaded.is_set():
            self.log("(Spracherkennung laedt noch, einmalig ggf. Download ...)")
            self.loaded.wait()
        if self.error:
            raise ListenError(self.error)

    def record(self, stop=None):
        """Record one utterance; returns float32 audio or None if nothing was said.

        stop: optional callable checked every block; True ends the recording early
        (e.g. Enter pressed). Whisper's own VAD then ignores leading silence.
        """
        blocks, levels = [], []
        try:
            with self.sd.InputStream(samplerate=RATE, channels=1, dtype="float32", blocksize=BLOCK) as stream:
                while True:
                    data, _ = stream.read(BLOCK)
                    block = data[:, 0].copy()
                    blocks.append(block)
                    levels.append(float(self.np.sqrt(self.np.mean(block * block))))
                    state, _ = find_speech(levels)
                    if stop is not None and stop():
                        return self.np.concatenate(blocks) if len(blocks) > 10 else None
                    if state == "silent":
                        return None
                    if state == "done":
                        return self.np.concatenate(blocks)
        except self.sd.PortAudioError as exc:
            raise ListenError("Mikrofonfehler: {}".format(exc)) from exc

    def transcribe(self, audio, fallback="de"):
        """Return (text, language). Only German and English are accepted."""
        self.wait_model()
        # The prompt nudges Whisper towards Buddy's command words ("Rest play" -> "Press play").
        options = {"beam_size": 1, "vad_filter": True, "initial_prompt": PROMPT}
        segments, info = self.model.transcribe(audio, **options)
        language = info.language
        if language not in LANGUAGES:
            segments, info = self.model.transcribe(audio, language=fallback, **options)
            language = fallback
        text = " ".join(segment.text.strip() for segment in segments).strip()
        # Whisper sometimes returns only the prompt or punctuation for noise.
        if text.strip(" .!?,") in ("", "Pixel Buddy") or text.strip() == PROMPT:
            text = ""
        return text, language
