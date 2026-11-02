"""Offline speech with the built-in Windows voices (System.Speech via PowerShell).

One PowerShell helper stays running; each request is one base64 JSON line on
its stdin, and it answers DONE (or ERR ...) after speaking. No extra packages.
"""
import base64
import json
import re
import subprocess
import sys
import threading
from xml.sax.saxutils import escape

PITCH = "+25%"  # A little higher sounds smaller and cuter.
RATE = 1        # System.Speech rate, -10 .. 10.
PREFERRED = {"de": ("Hedda", "Katja"), "en": ("Zira", "David")}

HELPER = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.__OUTPUT__()
$list = foreach ($v in $s.GetInstalledVoices()) { if ($v.Enabled) { $v.VoiceInfo.Name + '|' + $v.VoiceInfo.Culture.Name } }
[Console]::Out.WriteLine('READY ' + ($list -join ';'))
[Console]::Out.Flush()
while ($null -ne ($line = [Console]::In.ReadLine())) {
  try {
    $req = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($line)) | ConvertFrom-Json
    $s.SelectVoice($req.voice)
    $s.Rate = [int]$req.rate
    $s.SpeakSsml($req.ssml)
    [Console]::Out.WriteLine('DONE')
  } catch {
    [Console]::Out.WriteLine('ERR ' + $_.Exception.Message)
  }
  [Console]::Out.Flush()
}
"""


class VoiceError(Exception):
    pass


def _kill(proc):
    proc.kill()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        pass
    for pipe in (proc.stdin, proc.stdout):
        try:
            pipe.close()
        except (OSError, ValueError):
            pass


def clean_text(text):
    """Drop emoji, *stage directions* and markup characters the voice would read aloud."""
    text = re.sub(r"\*[^*]{0,60}\*", " ", text)
    text = "".join(ch for ch in text if (ord(ch) < 0x2190 or 0x2E80 <= ord(ch) < 0x1F000)
                   and ch not in "️‍")
    text = re.sub(r"[#_*~`<>|]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def build_ssml(text, culture, pitch=PITCH):
    return ('<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{}">'
            '<prosody pitch="{}">{}</prosody></speak>').format(culture, pitch, escape(text))


def pick_voice(voices, lang):
    """voices: {name: culture}. Prefer the cute default per language, then any match."""
    matching = {name: culture for name, culture in voices.items() if culture.lower().startswith(lang)}
    for wanted in PREFERRED.get(lang, ()):
        for name, culture in matching.items():
            if wanted in name:
                return name, culture
    if matching:
        return next(iter(matching.items()))
    return next(iter(voices.items()), (None, None))


class Voice:
    def __init__(self, log=print, silent=False):
        if sys.platform != "win32":
            raise VoiceError("Sprachausgabe gibt es nur unter Windows.")
        self.log = log
        self.silent = silent  # Tests: synthesize without playing audio.
        self.proc = None
        self.voices = {}
        self.on_done = None
        self.lock = threading.Lock()
        self._start()

    @property
    def speaking(self):
        return self.on_done is not None

    def _start(self):
        helper = HELPER.replace("__OUTPUT__", "SetOutputToNull" if self.silent else "SetOutputToDefaultAudioDevice")
        script = base64.b64encode(helper.encode("utf-16-le")).decode("ascii")
        try:
            proc = subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                 "-EncodedCommand", script],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, encoding="utf-8", errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError as exc:
            raise VoiceError("PowerShell nicht startbar: {}".format(exc)) from exc
        ready = proc.stdout.readline().strip()
        if not ready.startswith("READY"):
            _kill(proc)
            raise VoiceError("Windows-Sprachausgabe nicht verfuegbar.")
        voices = dict(item.split("|", 1) for item in ready[6:].split(";") if "|" in item)
        if not voices:
            _kill(proc)
            raise VoiceError("Keine Windows-Stimme installiert.")
        self.voices = voices
        self.proc = proc
        threading.Thread(target=self._read, args=(proc,), name="voice", daemon=True).start()

    def describe(self):
        return ", ".join("{}: {}".format(lang, pick_voice(self.voices, lang)[0]) for lang in ("de", "en"))

    def say(self, text, lang="de", on_done=None):
        """Speak in the background; on_done() runs when finished, failed or stopped."""
        self.stop()
        text = clean_text(text)
        if not text:
            if on_done:
                on_done()
            return
        if self.proc is None or self.proc.poll() is not None:
            self._start()
        name, culture = pick_voice(self.voices, lang)
        request = {"voice": name, "rate": RATE, "ssml": build_ssml(text, culture)}
        line = base64.b64encode(json.dumps(request).encode("utf-8")).decode("ascii")
        with self.lock:
            self.on_done = on_done or (lambda: None)
        try:
            self.proc.stdin.write(line + "\n")
            self.proc.stdin.flush()
        except OSError as exc:
            self._finish()
            self.proc = None
            raise VoiceError("Sprachausgabe abgebrochen: {}".format(exc)) from exc

    def stop(self):
        """Interrupt current speech by restarting the helper (rare, ~1 s)."""
        if not self.speaking:
            return
        proc, self.proc = self.proc, None
        if proc is not None:
            _kill(proc)
        self._finish()

    def close(self):
        self.stop()
        if self.proc is not None:
            proc, self.proc = self.proc, None
            try:
                proc.stdin.close()
                proc.wait(timeout=3)
            except (OSError, subprocess.TimeoutExpired):
                pass
            _kill(proc)

    def _finish(self):
        with self.lock:
            callback, self.on_done = self.on_done, None
        if callback:
            callback()

    def _read(self, proc):
        try:
            for line in proc.stdout:
                line = line.strip()
                if line.startswith("ERR"):
                    self.log("[Stimme] " + line[4:])
                if line == "DONE" or line.startswith("ERR"):
                    if proc is self.proc:
                        self._finish()
        except (OSError, ValueError):
            pass  # Pipe closed by stop()/close().
        # Helper ended unexpectedly while speaking: release the mouth animation.
        if proc is self.proc:
            self.proc = None
            self._finish()
