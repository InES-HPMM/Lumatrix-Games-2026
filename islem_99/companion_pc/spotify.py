"""Spotify Web API control (Premium needed for playback), standard library only.

Login: Authorization Code with PKCE, so only the Client ID is needed, never the
Client Secret. Tokens are stored outside the (OneDrive-synced) project in
%LOCALAPPDATA%\\PixelBuddy\\spotify.json and refreshed automatically.
"""
import base64
import hashlib
import json
import os
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API = "https://api.spotify.com/v1"
REDIRECT_PORT = 8888
REDIRECT_URI = "http://127.0.0.1:{}/callback".format(REDIRECT_PORT)
SCOPES = ("user-modify-playback-state user-read-playback-state "
          "user-read-currently-playing playlist-read-private")
TIMEOUT = 10


def default_path():
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "PixelBuddy", "spotify.json")


class SpotifyError(Exception):
    pass


def http(method, url, params=None, form=None, body=None, token=None):
    """Return (status, parsed JSON or None). Raises SpotifyError on network errors."""
    if params:
        url += "?" + urlencode(params)
    headers = {}
    data = None
    if form is not None:
        data = urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    elif method in ("PUT", "POST"):
        data = b""
    if token:
        headers["Authorization"] = "Bearer " + token
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            status, raw = response.status, response.read(2 * 1024 * 1024)
    except HTTPError as exc:
        with exc:
            status, raw = exc.code, exc.read(64 * 1024)
    except (URLError, OSError) as exc:
        raise SpotifyError("Spotify nicht erreichbar ({})".format(getattr(exc, "reason", exc))) from exc
    try:
        return status, json.loads(raw) if raw else None
    except ValueError:
        return status, None


class Spotify:
    def __init__(self, path=None, device=None):
        self.path = path or default_path()
        self.device = device  # Optional preferred device name (part of it is enough).
        self.data = {}
        self.lock = threading.Lock()
        try:
            with open(self.path, encoding="utf-8") as f:
                self.data = json.load(f)
        except (OSError, ValueError):
            self.data = {}

    @property
    def configured(self):
        return bool(self.data.get("client_id") and self.data.get("refresh_token"))

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f)
        os.replace(tmp, self.path)

    def logout(self):
        self.data = {}
        try:
            os.remove(self.path)
        except OSError:
            pass

    # --- Login (PKCE) ----------------------------------------------------------

    def login(self, client_id, open_browser=True, timeout=180, log=print):
        client_id = client_id.strip()
        if not client_id.isalnum() or len(client_id) != 32:
            raise SpotifyError("Das sieht nicht wie eine Spotify Client-ID aus (32 Zeichen).")
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        state = secrets.token_urlsafe(16)
        url = AUTH_URL + "?" + urlencode({
            "client_id": client_id, "response_type": "code", "redirect_uri": REDIRECT_URI,
            "code_challenge_method": "S256", "code_challenge": challenge, "scope": SCOPES, "state": state})
        result = {}

        class Callback(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                query = parse_qs(urlparse(self.path).query)
                if urlparse(self.path).path != "/callback":
                    self.send_response(404)
                    self.end_headers()
                    return
                if query.get("state", [""])[0] != state:
                    result["error"] = "state mismatch"
                else:
                    result["code"] = query.get("code", [""])[0]
                    result["error"] = query.get("error", [""])[0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                ok = result.get("code") and not result.get("error")
                self.wfile.write(("<h2>Pixel Buddy: {}</h2><p>Du kannst dieses Fenster schliessen.</p>".format(
                    "Spotify verbunden!" if ok else "Anmeldung fehlgeschlagen")).encode())

        try:
            server = HTTPServer(("127.0.0.1", REDIRECT_PORT), Callback)
        except OSError as exc:
            raise SpotifyError("Port {} ist belegt.".format(REDIRECT_PORT)) from exc
        server.timeout = 1
        log("Browser-Anmeldung bei Spotify. Falls sich kein Browser oeffnet, diese Adresse oeffnen:")
        log(url)
        if open_browser:
            webbrowser.open(url)
        end = time.monotonic() + timeout
        try:
            while "error" not in result and time.monotonic() < end:
                server.handle_request()
        finally:
            server.server_close()
        if not result:
            raise SpotifyError("Keine Anmeldung innerhalb von {} s.".format(timeout))
        if result.get("error") or not result.get("code"):
            raise SpotifyError("Spotify-Anmeldung abgelehnt: " + (result.get("error") or "kein Code"))
        status, token = http("POST", TOKEN_URL, form={
            "grant_type": "authorization_code", "code": result["code"], "redirect_uri": REDIRECT_URI,
            "client_id": client_id, "code_verifier": verifier})
        if status != 200 or not token or "refresh_token" not in token:
            raise SpotifyError("Token-Abruf fehlgeschlagen (HTTP {}): {}".format(status, (token or {}).get("error")))
        self.data = {"client_id": client_id}
        self._store(token)

    def _store(self, token):
        self.data["access_token"] = token["access_token"]
        self.data["expires_at"] = time.time() + int(token.get("expires_in", 3600)) - 60
        if token.get("refresh_token"):
            self.data["refresh_token"] = token["refresh_token"]
        self._save()

    def _token(self, force=False):
        if not self.configured:
            raise SpotifyError("Spotify ist noch nicht verbunden: python -m companion_pc --spotify-login")
        if force or time.time() >= self.data.get("expires_at", 0):
            status, token = http("POST", TOKEN_URL, form={
                "grant_type": "refresh_token", "refresh_token": self.data["refresh_token"],
                "client_id": self.data["client_id"]})
            if status != 200 or not token or "access_token" not in token:
                raise SpotifyError("Spotify-Anmeldung abgelaufen. Neu verbinden: python -m companion_pc --spotify-login")
            self._store(token)
        return self.data["access_token"]

    # --- API ---------------------------------------------------------------------

    def api(self, method, path, params=None, body=None):
        with self.lock:
            status, data = http(method, API + path, params=params, body=body, token=self._token())
            if status == 401:
                status, data = http(method, API + path, params=params, body=body, token=self._token(force=True))
        if status in (200, 201, 202, 204):
            return data
        error = data.get("error") if isinstance(data, dict) else None
        error = error if isinstance(error, dict) else {}
        reason, message = error.get("reason", ""), error.get("message", "")
        if status == 403 and (reason == "PREMIUM_REQUIRED" or "premium" in message.lower()):
            raise SpotifyError("Spotify Premium ist fuer die Steuerung noetig.")
        if status == 404 and (reason == "NO_ACTIVE_DEVICE" or "device" in message.lower()):
            raise NoDevice()
        if status == 429:
            raise SpotifyError("Spotify: zu viele Anfragen, kurz warten.")
        raise SpotifyError("Spotify HTTP {}: {}".format(status, message or reason or "Fehler"))

    def _target(self):
        """Pick the device to play on: preferred name, this PC's Spotify app, other apps, web player last.

        Spotify reports browser web players as type "Computer" too; a background
        browser tab often stays silent (autoplay blocking), so it is only a fallback.
        """
        devices = [d for d in (self.api("GET", "/me/player/devices") or {}).get("devices") or []
                   if d and d.get("id") and not d.get("is_restricted")]
        if not devices:
            raise SpotifyError("Spotify ist auf keinem Geraet offen. Bitte die Spotify-App starten.")
        wanted = (self.device or "").lower()
        here = os.environ.get("COMPUTERNAME", "").lower()

        def rank(device):
            name = (device.get("name") or "").lower()
            web = name.startswith("web player")
            return (not (wanted and wanted in name), not (here and name == here), web,
                    device.get("type") != "Computer", not device.get("is_active"))
        return min(devices, key=rank)

    def _with_device(self, method, path, body=None):
        """Run a player command on the target device, moving playback there first if needed."""
        device = self._target()
        if path == "/me/player/play":
            # play?device_id= starts there directly (and transfers from another device).
            return self.api(method, path + "?" + urlencode({"device_id": device["id"]}), body=body)
        if not device.get("is_active"):
            self.api("PUT", "/me/player", body={"device_ids": [device["id"]], "play": True})
            time.sleep(0.5)  # Let Spotify finish the transfer before skipping.
        return self.api(method, path)

    def devices(self):
        """Human readable device list, the one Buddy would use marked with ->."""
        target = self._target()
        lines = []
        for d in (self.api("GET", "/me/player/devices") or {}).get("devices") or []:
            lines.append("{} {} ({}{})".format("->" if d.get("id") == target["id"] else "  ", d.get("name"),
                                               d.get("type"), ", aktiv" if d.get("is_active") else ""))
        return "\n".join(lines)

    # Player commands return plain facts from Spotify, never invented text:
    # {"what": "'Beat It' by Michael Jackson" or None, "playing": bool, "changed": bool, "volume": int}

    def pause(self):
        try:
            self.api("PUT", "/me/player/pause")
        except NoDevice:
            pass  # Nothing is playing anyway.
        return {"what": None}

    def resume(self):
        self._with_device("PUT", "/me/player/play")
        return self._now()

    def _current_id(self):
        try:
            data = self.api("GET", "/me/player/currently-playing")
        except SpotifyError:
            return None
        return ((data or {}).get("item") or {}).get("id")

    def next(self):
        before = self._current_id()
        self._with_device("POST", "/me/player/next")
        return self._now(changed_from=before)

    def previous(self):
        before = self._current_id()
        self._with_device("POST", "/me/player/previous")
        return self._now(changed_from=before)

    def volume(self, delta):
        state = self.api("GET", "/me/player") or {}
        current = (state.get("device") or {}).get("volume_percent")
        if current is None:
            raise SpotifyError("Lautstaerke kann auf diesem Geraet nicht geaendert werden.")
        target = max(0, min(100, current + delta))
        self.api("PUT", "/me/player/volume?" + urlencode({"volume_percent": target}))
        return {"volume": target}

    def now_playing(self):
        return self._now()

    def _now(self, changed_from=None):
        """Current song; after a skip wait (max ~2.5 s) until Spotify reports a different one."""
        data = None
        for attempt in range(6 if changed_from else 1):
            if changed_from:
                time.sleep(0.4)
            try:
                data = self.api("GET", "/me/player/currently-playing")
            except SpotifyError:
                return {"what": None}
            current = ((data or {}).get("item") or {}).get("id")
            if not changed_from or (current and current != changed_from):
                break  # An empty answer during the switch is not the new song yet.
        item = (data or {}).get("item")
        return {"what": describe(item) if item else None, "playing": bool((data or {}).get("is_playing")),
                "changed": bool(item) and item.get("id") != changed_from}

    def play(self, request):
        """Play a search request from music.parse_play (kind, query)."""
        kind, query = request
        if kind == "playlist":
            uri, label = self._find_playlist(query)
            self._with_device("PUT", "/me/player/play", body={"context_uri": uri})
            return {"what": "'{}'".format(label)}
        kinds = {"artist": "artist", "album": "album", "track": "track", "genre": "playlist"}
        found = (self.api("GET", "/search", params={"q": query, "type": kinds[kind], "limit": 1}) or {})
        items = (found.get(kinds[kind] + "s") or {}).get("items") or []
        items = [item for item in items if item]
        if not items:
            raise SpotifyError("Nichts gefunden fuer '{}'".format(query))
        item = items[0]
        album = (item.get("album") or {}).get("uri") if kind == "track" else None
        if album:
            # Start inside its album, so "next song" has somewhere to go.
            body = {"context_uri": album, "offset": {"uri": item["uri"]}}
        elif kind == "track":
            body = {"uris": [item["uri"]]}
        else:
            body = {"context_uri": item["uri"]}
        self._with_device("PUT", "/me/player/play", body=body)
        return {"what": describe(item)}

    def _find_playlist(self, name):
        wanted = name.lower()
        page = self.api("GET", "/me/playlists", params={"limit": 50}) or {}
        for item in page.get("items") or []:
            if item and wanted in (item.get("name") or "").lower():
                return item["uri"], item["name"]
        found = self.api("GET", "/search", params={"q": name, "type": "playlist", "limit": 1}) or {}
        items = [i for i in ((found.get("playlists") or {}).get("items") or []) if i]
        if not items:
            raise SpotifyError("Keine Playlist '{}' gefunden".format(name))
        return items[0]["uri"], items[0]["name"]


class NoDevice(SpotifyError):
    pass


def describe(item):
    """'Bohemian Rhapsody' by Queen / an artist / an album."""
    name = item.get("name", "?")
    artists = ", ".join(a.get("name", "") for a in item.get("artists") or [] if a)
    return "'{}' by {}".format(name, artists) if artists else "'{}'".format(name)
