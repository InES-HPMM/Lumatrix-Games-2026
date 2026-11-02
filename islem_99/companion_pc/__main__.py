"""Run on Windows: python -m companion_pc [--check] [--pico-port COM7] [--no-pico] [--no-voice]."""
import argparse
import sys
import time

from .console import drain_keys, enter_pressed, read_line
from .conversation import Conversation, detect_language
from .actions import ACTIONS, describe_event, detect_action
from .emotions import ANIMATIONS, DEFAULT_INTENSITY, EMOTIONS, show_command
from .listen import MODELS as STT_MODELS, Listener, ListenError
from .music import detect_music, maybe_music, outcome, reply as music_reply, run as run_music
from .ollama_client import MODELS, OllamaClient, OllamaError
from .pico_link import RESULTS, PicoLink, PicoUnavailable, find_pico_ports
from .spotify import Spotify, SpotifyError
from .timer import control as control_timer, detect_timer, parse_duration, reply as timer_reply
from .voice import Voice, VoiceError
from .web import WebError, lookup, plan_lookup

HELP = ("Enter auf leerer Zeile = sprechen (Mikrofon). Befehle: /act <aktion>, /web <suche>, /spotify, "
        "/wetter [ort], /timer [minuten|stop], /emotion <name> [animation], /emotions, /pico, /voice, /say <text>, "
        "/clear, /check, /exit")


class Web:
    """Internet lookups for one session; remembers the last weather place."""

    def __init__(self, city=None):
        self.city = city  # Home town for weather questions without a place.
        self.last = None  # Previous weather plan, for "Und morgen?" follow-ups.

    def plan(self, text):
        plan = plan_lookup(text, self.last)
        if not (plan and plan[0] == "weather"):
            self.last = None  # Follow-ups only directly after a weather answer.
        return plan

    def run(self, plan, lang):
        """Return info text for the AI; failures become a short note instead of an error."""
        if plan[0] == "weather":
            print("\U0001F310 Wetter:", plan[1] or self.city or "(kein Ort)",
                  ("heute", "morgen", "uebermorgen")[plan[2]], flush=True)
        else:
            print("\U0001F310 Suche im Internet:", plan[1], flush=True)
        try:
            info, source, place = lookup(plan, lang, self.city)
        except WebError as exc:
            print("Internet:", exc)
            return ("You tried to look this up on the internet, but it failed ({}). "
                    "Tell the user briefly that you could not find it right now.".format(exc))
        if plan[0] == "weather" and place:
            self.last = ("weather", place, plan[2])
        print("   Quelle:", source)
        return info


def hear(listener, voice, link, language):
    """Push-to-talk: record until a short pause, return the recognised text or ''."""
    if voice:
        voice.stop()  # Do not record Buddy's own voice.
    try:
        listener.wait_model()
    except ListenError as exc:
        print("Mikrofon:", exc)
        return ""
    if link:
        link.send({"cmd": "listen"})
    print("\U0001F3A4 Ich hoere zu ... (Enter, Joystick oder kurze Pause beendet, Strg+C bricht ab)",
          flush=True)
    text = ""
    joystick = link.mic_pressed if link else (lambda: False)
    try:
        drain_keys()  # Only Enter / joystick pressed from now on ends the recording.
        joystick()
        audio = listener.record(lambda: enter_pressed() or joystick())
        if audio is None:
            print("(Nichts gehoert.)")
        else:
            if link:
                link.send({"cmd": "think"})
            text, _ = listener.transcribe(audio, language)
            print("You (Stimme):", text if text else "(nichts verstanden)")
    except KeyboardInterrupt:
        print("(Abgebrochen.)")
    except ListenError as exc:
        print("Mikrofon:", exc)
    if not text and link:
        link.send({"cmd": "idle"})
    return text


def spotify_login(spotify):
    """Interactive one-time Spotify connection (PKCE, Client ID only)."""
    print("Spotify verbinden (einmalig). Benoetigt Spotify Premium.")
    print("1. https://developer.spotify.com/dashboard -> deine App -> Settings")
    print("2. Redirect URI eintragen und speichern:  http://127.0.0.1:8888/callback")
    print("3. Bei 'APIs used' Web API anhaken. Das Client Secret wird NICHT gebraucht.")
    client_id = input("Client ID: ").strip()
    try:
        spotify.login(client_id)
    except SpotifyError as exc:
        print("Spotify:", exc)
        return 1
    print("Spotify verbunden. Token gespeichert in", spotify.path)
    return 0


def control_music(spotify, command, lang):
    """Run a Spotify command; returns Buddy's fixed reply (text, face, animation).

    The small local model claimed success after failures and invented song titles,
    so music replies only use what Spotify really reported.
    """
    label = command[0] if command[0] != "play" else "play {} '{}'".format(*command[1])
    print("\U0001F3B5 Spotify:", label, flush=True)
    if not spotify.configured:
        print("   Spotify ist nicht verbunden: python -m companion_pc --spotify-login")
        return music_reply("not_connected", lang)
    try:
        facts = run_music(spotify, command)
    except SpotifyError as exc:
        print("   Spotify:", exc)
        return music_reply("failed", lang, reason=str(exc))
    kind = outcome(command, facts)
    print("  ", kind, "|", facts.get("what") or facts.get("volume") or "")
    return music_reply(kind, lang, **facts)


def run_action(link, action):
    """Run a pet action on the Pico and print what happened; returns the result."""
    result = link.act(action) if link else None
    if result is None:
        print("Aktion:", action, "(Pico nicht verbunden)" if not (link and link.ready) else "(keine Antwort)")
    else:
        print("Aktion:", action, "->", RESULTS.get(result, "ok"))
    return result


def manual_action(link, words):
    """/act feed -> run a pet action without asking the AI."""
    if len(words) < 2 or words[1] not in ACTIONS:
        print("Aktionen:", ", ".join(ACTIONS))
        return
    run_action(link, words[1])


def speak(voice, link, text, lang):
    """Speak in the background; the Pico moves the mouth until the voice is done."""
    if voice is None:
        return
    voice.stop()  # Release the previous sentence before starting a new one.
    done = None
    if link:
        link.send({"cmd": "talk", "ms": 60000})
        done = lambda: link.send({"cmd": "talk", "ms": 0})
    try:
        voice.say(text, lang, done)
    except VoiceError as exc:
        print("Stimme:", exc)
        if done:
            done()


def timer_command(link, command, lang):
    """Run a timer command on the Pico; returns Buddy's fixed reply (text, face, animation)."""
    kind, seconds = control_timer(link, command)
    print("\u23F0 Timer:", command[0], "->", kind, "" if seconds is None else "({} s)".format(seconds), flush=True)
    return timer_reply(kind, lang, seconds)


def manual_timer(link, words, lang):
    """/timer 15 -> 15 minutes, /timer 90s, /timer stop, /timer -> time left."""
    rest = " ".join(words[1:]).lower()
    if not rest:
        command = ("left",)
    elif rest in ("stop", "stopp", "cancel", "aus", "ab"):
        command = ("cancel",)
    else:
        if rest[:-1].isdigit() and rest[-1] == "s":
            rest = rest[:-1] + " sekunden"
        seconds = parse_duration(rest, bare_minutes=True)
        if seconds is None:
            print("Beispiele: /timer 15, /timer 90s, /timer stop, /timer")
            return
        command = ("start", seconds)
    print(timer_command(link, command, lang)[0])


def announce_timer(link, voice, lang):
    """The Pico reported an ended timer: say so (the matrix blinks by itself)."""
    kind = "done_total" if link.timer_total else "done"
    text = timer_reply(kind, lang, link.timer_total)[0]
    link.timer_total = None
    print("\u23F0 Buddy:", text, flush=True)
    speak(voice, link, text, lang)


def manual_emotion(link, words):
    """/emotion excited star -> show without asking the AI."""
    if len(words) < 2 or words[1] not in EMOTIONS:
        print("Emotionen:", ", ".join(EMOTIONS), "| Animationen:", ", ".join(ANIMATIONS))
        return
    animation = words[2] if len(words) > 2 else None
    if animation is not None and animation not in ANIMATIONS:
        print("Unbekannte Animation. Erlaubt:", ", ".join(ANIMATIONS))
        return
    command = show_command(words[1], animation, DEFAULT_INTENSITY)
    sent = link is not None and link.send(command)
    print("LED:", command["face"], "/", command["anim"], "" if sent else "(Pico nicht verbunden)")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Pixel Buddy: lokaler Ollama-Chat mit LED-Matrix")
    parser.add_argument("--model", choices=MODELS, default=MODELS[0])
    parser.add_argument("--port", type=int, default=11434, help="lokaler Ollama-Port")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--pico-port", help="COM-Port des Pico, z. B. COM7 (Standard: automatisch)")
    parser.add_argument("--no-pico", action="store_true", help="nur chatten, keinen COM-Port oeffnen")
    parser.add_argument("--no-voice", action="store_true", help="Antworten nicht vorlesen")
    parser.add_argument("--no-mic", action="store_true", help="keine Spracheingabe")
    parser.add_argument("--no-web", action="store_true", help="keine Internetabfragen (Wetter, Suche)")
    parser.add_argument("--city", help="Ort fuer Wetterfragen ohne Ortsangabe, z. B. Zuerich")
    parser.add_argument("--spotify-login", action="store_true", help="Spotify einmalig verbinden")
    parser.add_argument("--spotify-logout", action="store_true", help="gespeichertes Spotify-Token loeschen")
    parser.add_argument("--no-spotify", action="store_true", help="keine Musikbefehle")
    parser.add_argument("--spotify-device", help="bevorzugtes Spotify-Geraet (Teil des Namens), Standard: App auf diesem PC")
    parser.add_argument("--stt-model", choices=STT_MODELS, default="base",
                        help="Whisper-Modell: base = schnell, small = genauer")
    parser.add_argument("--no-ai", action="store_true", help="ohne Ollama: nur /emotion-Tests an der Matrix")
    parser.add_argument("--list-ports", action="store_true", help="erkannte Pico-Ports anzeigen")
    parser.add_argument("--check", action="store_true", help="Lokale API und installiertes Modell pruefen")
    parser.add_argument("--debug", action="store_true", help="Antwortdauer und USB-Verkehr anzeigen")
    args = parser.parse_args(argv)

    if args.spotify_login:
        return spotify_login(Spotify())
    if args.spotify_logout:
        Spotify().logout()
        print("Spotify-Token geloescht.")
        return 0
    if args.list_ports:
        ports = find_pico_ports()
        print("Pico-Ports:", ", ".join(ports) if ports else "keine gefunden")
        return 0
    client = chat = None
    if not args.no_ai:
        try:
            client = OllamaClient(args.model, args.port, args.timeout)
            client.check()
        except (OllamaError, ValueError) as exc:
            print("Start nicht moeglich:", exc, file=sys.stderr)
            print("Nur LED-Test ohne AI: python -m companion_pc --no-ai", file=sys.stderr)
            return 1
        print("Ollama bereit:", client.base_url, "|", client.model)
        if args.check:
            return 0
        chat = Conversation(client)

    link = None
    if not args.no_pico:
        try:
            link = PicoLink(args.pico_port, args.debug).start()
        except PicoUnavailable as exc:
            print("LED-Matrix deaktiviert:", exc)
        else:
            # Make a missing matrix obvious instead of a log line that scrolls away.
            if link.wait_ready(4):
                print("LED-Matrix:", link.status())
            else:
                print("!!! LED-Matrix NICHT verbunden:", link.status())
                print("    Chat und Stimme laufen trotzdem; neuer Versuch alle 2 s. Status: /pico")

    voice = None
    if not args.no_voice:
        try:
            voice = Voice()
            print("Stimme bereit:", voice.describe())
        except VoiceError as exc:
            print("Stimme deaktiviert:", exc)

    spotify = None if args.no_spotify else Spotify(device=args.spotify_device)
    if spotify:
        print("Spotify:", "verbunden" if spotify.configured else
              "nicht verbunden (einmalig: python -m companion_pc --spotify-login)")

    web = None if args.no_web else Web(args.city)
    if web:
        print("Internet: Wetter (Open-Meteo) und Suche (DuckDuckGo/Wikipedia) nur bei Bedarf."
              + ("" if args.city else " Tipp: --city <Ort>"))

    listener = None
    if not args.no_mic:
        try:
            listener = Listener(args.stt_model)
            print("Mikrofon bereit (Whisper {}, laedt im Hintergrund).".format(args.stt_model))
        except ListenError as exc:
            print("Spracheingabe deaktiviert:", exc)

    print("Pixel Buddy is awake! \U0001F49A")
    print(HELP)
    try:
        while True:
            try:
                # Enter on an empty line or a joystick press on the Pico starts the microphone.
                lang = chat.language if chat else "de"
                if link and link.timer_rang():
                    announce_timer(link, voice, lang)
                wake = (lambda: link.timer_pending() or link.mic_pressed()) if link else None
                text = read_line("\nYou: ", wake)
                if text is None and link and link.timer_rang():
                    announce_timer(link, voice, lang)  # Woken by the timer, not the joystick.
                    continue
                text = (text or "").strip()
                if text in ("/exit", "/quit"):
                    return 0
                spoken = not text
                if not text:
                    if listener is None:
                        print("(Mikrofon ist aus - Start ohne --no-mic, Pakete siehe README)")
                        continue
                    text = hear(listener, voice, link, chat.language if chat else "de")
                    if not text:
                        continue
                    if chat is None:
                        continue  # --no-ai: only show what was recognised.
                words = text.split()
                if words[0] == "/act":
                    manual_action(link, words)
                    continue
                if words[0] in ("/web", "/wetter"):
                    if web is None:
                        print("Internet ist aus (--no-web).")
                        continue
                    rest = text[len(words[0]):].strip()
                    if words[0] == "/web" and not rest:
                        print("Beispiel: /web Wer hat das Matterhorn zuerst bestiegen")
                        continue
                    plan = ("search", rest) if words[0] == "/web" else ("weather", rest or None, 0)
                    print(web.run(plan, detect_language(rest, chat.language if chat else "de")))
                    continue
                if words[0] == "/timer":
                    manual_timer(link, words, lang)
                    continue
                if words[0] in ("/emotion", "/emotions"):
                    manual_emotion(link, words)
                    continue
                if text == "/voice":
                    if voice:
                        voice.close()
                        voice = None
                        print("Stimme aus.")
                    else:
                        try:
                            voice = Voice()
                            print("Stimme an:", voice.describe())
                        except VoiceError as exc:
                            print("Stimme nicht verfuegbar:", exc)
                    continue
                if words[0] == "/say":
                    sample = text[4:].strip() or "Hallo, ich bin Pixel Buddy!"
                    if voice is None:
                        print("Stimme ist aus (/voice).")
                    speak(voice, link, sample, detect_language(sample))
                    if link and not link.ready:
                        print("(LED-Matrix nicht verbunden - /pico)")
                    continue
                if text == "/spotify":
                    if spotify and spotify.configured:
                        try:
                            facts = spotify.now_playing()
                            print(music_reply(outcome(("now",), facts), "de", **facts)[0])
                            print("Geraete (-> = wird verwendet):")
                            print(spotify.devices())
                        except SpotifyError as exc:
                            print("Spotify:", exc)
                    else:
                        print("Spotify nicht verbunden: python -m companion_pc --spotify-login")
                    continue
                if text == "/pico":
                    print("Pico:", link.status() if link else "deaktiviert")
                    continue
                if text == "/clear":
                    if chat:
                        chat.clear()
                    print("Gespraechskontext geloescht.")
                    continue
                if text == "/check":
                    print("Ollama bereit:", client.check() if client else "deaktiviert (--no-ai)")
                    continue
                if text.startswith("/") or chat is None:
                    print(HELP)
                    continue
                if voice:
                    voice.stop()  # A new message interrupts Buddy.
                timer = detect_timer(text)
                music = detect_music(text) if spotify and not timer else None
                action = None if (music or timer) else detect_action(text)
                event = ""
                if action:
                    event = describe_event(action, run_action(link, action))
                if link:
                    link.send({"cmd": "think"})
                lang = detect_language(text, chat.language)
                canned = None  # Fixed reply (text, face, animation) instead of asking the AI.
                if timer:
                    canned = timer_command(link, timer, lang)
                elif music:
                    canned = control_music(spotify, music, lang)
                elif spotify and not action and maybe_music(text):
                    print("\U0001F3B5 (Kein Musikbefehl erkannt - nichts an Spotify gesendet)")
                    canned = music_reply("unclear", lang)
                plan = web.plan(text) if web and not canned else None
                if plan:
                    info = web.run(plan, lang)
                    event = "\n".join(part for part in (event, info) if part)
                start = time.monotonic()
                if canned:
                    result = {"reply": canned[0], "face": canned[1], "animation": canned[2],
                              "emotion": "fixed", "intensity": 0.6, "fixed": []}
                    chat.remember(text, result["reply"], lang)
                else:
                    print("Buddy denkt ...", flush=True)
                    try:
                        result = chat.send(text, link.pet if link else None, event)
                    except BaseException:
                        if link:
                            link.send({"cmd": "idle"})
                        raise
                if link:
                    link.mic_pressed()  # Presses while Buddy was thinking must not cut his voice.
                print("Buddy:", result["reply"])
                if canned:
                    print("Gesicht:", result["face"], "({})".format(result["animation"]))
                else:
                    print("Emotion:", result["emotion"],
                          "({}, {:.1f})".format(result["animation"], result["intensity"]))
                if link:
                    if canned:
                        # Timer replies stay short, so the countdown shows right after Buddy spoke.
                        link.send({"cmd": "show", "face": result["face"], "anim": result["animation"],
                                   "ms": 1500 if timer else 5500})
                    else:
                        link.send(show_command(result["emotion"], result["animation"], result["intensity"]))
                speak(voice, link, result["reply"], chat.language)
                if link and not link.ready:
                    print("(LED-Matrix nicht verbunden - /pico)")
                if spoken:
                    drain_keys()  # A stray Enter must not interrupt Buddy's voice.
                if args.debug:
                    print("[lokal: {:.1f}s, {} gespeicherte Gespraechspaare{}]".format(
                        time.monotonic() - start, len(chat.history) // 2,
                        ", ersetzt: " + ", ".join(result["fixed"]) if result["fixed"] else ""))
            except (OllamaError, ValueError) as exc:
                print("Hinweis:", exc)
                print("Nach Beheben erneut senden; der bisherige Kontext bleibt erhalten.")
    except (KeyboardInterrupt, EOFError):
        print("\nBis bald!")
        return 0
    finally:
        if voice:
            voice.close()
        if link:
            link.close()


if __name__ == "__main__":
    raise SystemExit(main())
