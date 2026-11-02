"""Ollama HTTP client using only the Python standard library."""
import json
import socket
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

MODELS = ("llama3.2:3b", "llama3.2:1b")


class OllamaError(Exception):
    """Recoverable connection, model or response error."""


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class OllamaClient:
    def __init__(self, model="llama3.2:3b", port=11434, timeout=120):
        if model not in MODELS:
            raise ValueError("Nur lokale llama3.2:3b/1b Modelle werden unterstuetzt.")
        if not 1 <= port <= 65535 or not 1 <= timeout <= 600:
            raise ValueError("Port muss 1-65535, Timeout 1-600 Sekunden sein.")
        self.model = model
        self.base_url = "http://127.0.0.1:" + str(port)
        self.timeout = timeout
        # Do not send localhost conversations through corporate/system proxies.
        self.opener = build_opener(ProxyHandler({}), NoRedirects())

    def _request(self, path, payload=None, timeout=None):
        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(self.base_url + path, data=data,
                          headers={"Content-Type": "application/json"})
        try:
            with self.opener.open(request, timeout=timeout or self.timeout) as response:
                raw = response.read(1024 * 1024 + 1)
        except HTTPError as exc:
            with exc:
                detail = exc.read(2048).decode("utf-8", errors="replace")
            if exc.code == 404 and path == "/api/chat":
                raise OllamaError("Modell fehlt. Ausfuehren: ollama pull " + self.model) from exc
            if 300 <= exc.code < 400:
                raise OllamaError("HTTP-Weiterleitung abgelehnt: nur lokale API erlaubt.") from exc
            raise OllamaError("Ollama HTTP {}: {}".format(exc.code, detail[:300])) from exc
        except (TimeoutError, socket.timeout) as exc:
            raise OllamaError("Ollama antwortet zu langsam. Erneut versuchen oder --timeout 240 / --model llama3.2:1b verwenden.") from exc
        except (URLError, OSError, HTTPException) as exc:
            raise OllamaError("Ollama nicht erreichbar unter {}. Ollama starten (ollama serve) und erneut versuchen.".format(self.base_url)) from exc
        if len(raw) > 1024 * 1024:
            raise OllamaError("Ollama-Antwort ist unerwartet gross.")
        try:
            result = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise OllamaError("Ollama hat kein gueltiges JSON geliefert.") from exc
        if not isinstance(result, dict):
            raise OllamaError("Unerwartetes Ollama-Antwortformat.")
        if result.get("error"):
            raise OllamaError("Ollama meldet: " + str(result["error"])[:300])
        return result

    def check(self):
        result = self._request("/api/tags", timeout=min(self.timeout, 20))
        models = result.get("models")
        if not isinstance(models, list):
            raise OllamaError("Ollama liefert keine gueltige Modellliste.")
        selected = next((item for item in models if isinstance(item, dict)
                         and item.get("name") == self.model), None)
        if selected is None:
            raise OllamaError("Ollama laeuft, aber das Modell fehlt. Ausfuehren: ollama pull " + self.model)
        if selected.get("remote_host") or selected.get("remote_model"):
            raise OllamaError("Cloud-Modell abgelehnt. Bitte ein lokales llama3.2-Modell laden.")
        return self.model

    def chat(self, messages, schema=None):
        """Return the reply text; with a JSON schema Ollama returns matching JSON text."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "keep_alive": "5m",
            "options": {"num_ctx": 4096, "num_predict": 256, "temperature": 0.7},
        }
        if schema is not None:
            payload["format"] = schema
        result = self._request("/api/chat", payload)
        message = result.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise OllamaError("Ollama-Antwort enthaelt keinen Antworttext.")
        reply = message["content"].strip()
        if not reply or result.get("done") is not True:
            raise OllamaError("Ollama hat keine vollstaendige Antwort geliefert.")
        return reply
