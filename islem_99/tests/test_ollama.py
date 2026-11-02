"""Real loopback HTTP tests with a small Ollama stub; no model download needed."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import URLError

from companion_pc.conversation import Conversation
from companion_pc.ollama_client import OllamaClient, OllamaError


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({"models": self.server.models}).encode())

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.requests.append((self.path, data))
        self.send_response(self.server.status)
        if self.server.status == 302:
            self.send_header("Location", "https://example.com/never-follow")
        self.end_headers()
        self.wfile.write(self.server.reply)


class OllamaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.server.models = [{"name": "llama3.2:3b"}]
        self.server.status = 200
        self.server.requests = []
        self.server.reply = json.dumps({"message": {"content": "Juhu, gut gemacht!"}, "done": True}).encode()
        self.client = OllamaClient(port=self.server.server_port)

    def test_real_http_chat_unicode_and_history(self):
        self.assertEqual(self.client.check(), "llama3.2:3b")
        chat = Conversation(self.client)
        result = chat.send("Ich bin müde.")
        # Plain text instead of JSON: keep the text, fall back to a neutral face.
        self.assertEqual(result["reply"], "Juhu, gut gemacht!")
        self.assertEqual(result["emotion"], "neutral")
        chat.send("Was habe ich gesagt?")
        path, request = self.server.requests[-1]
        self.assertEqual(path, "/api/chat")
        self.assertFalse(request["stream"])
        self.assertIn("excited", request["format"]["properties"]["emotion"]["enum"])
        self.assertEqual(request["options"]["num_ctx"], 4096)
        self.assertEqual(request["messages"][1]["content"], "Ich bin müde.")
        self.assertEqual([x["role"] for x in request["messages"]],
                         ["system", "user", "assistant", "user"])

    def test_missing_or_remote_model(self):
        self.server.models = []
        with self.assertRaisesRegex(OllamaError, "ollama pull"):
            self.client.check()
        self.server.models = [{"name": "llama3.2:3b", "remote_host": "example.com"}]
        with self.assertRaisesRegex(OllamaError, "Cloud"):
            self.client.check()

    def test_service_stopped_and_timeout(self):
        with patch.object(self.client.opener, "open", side_effect=URLError("refused")):
            with self.assertRaisesRegex(OllamaError, "nicht erreichbar"):
                self.client.check()
        with patch.object(self.client.opener, "open", side_effect=TimeoutError()):
            with self.assertRaisesRegex(OllamaError, "langsam"):
                self.client.chat([])

    def test_bad_json_and_missing_reply(self):
        for raw in (b"not JSON", b"[]", b"{}", b'{"message":{"content":""},"done":true}',
                    b'{"message":{"content":"partial"},"done":false}'):
            self.server.reply = raw
            with self.assertRaises(OllamaError):
                self.client.chat([])

    def test_http_failure_no_history_then_recovery(self):
        chat = Conversation(self.client)
        chat.send("Hallo")
        saved = chat.history[:]
        self.server.status = 503
        with self.assertRaises(OllamaError):
            chat.send("Noch da?")
        self.assertEqual(chat.history, saved)
        self.server.status = 200
        chat.send("Noch da?")
        self.assertEqual(len(chat.history), 4)

    def test_structured_reply_is_validated(self):
        content = json.dumps({"reply": "Yaaay!", "emotion": "EXCITED",
                              "animation": "sparkling_eyes", "intensity": 7})
        self.server.reply = json.dumps({"message": {"content": content}, "done": True}).encode()
        result = Conversation(self.client).send("Bestanden!")
        self.assertEqual((result["reply"], result["emotion"], result["animation"], result["intensity"]),
                         ("Yaaay!", "excited", "star", 1.0))
        self.assertEqual(result["fixed"], ["animation"])
        self.server.reply = json.dumps({"message": {"content": '{"emotion":"happy"}'}, "done": True}).encode()
        with self.assertRaises(OllamaError):
            Conversation(self.client).send("Hallo")

    def test_redirect_is_rejected(self):
        self.server.status = 302
        with self.assertRaisesRegex(OllamaError, "Weiterleitung"):
            self.client.chat([])

    def test_context_limits_clear_and_input(self):
        chat = Conversation(self.client)
        for i in range(12):
            chat.send("Nachricht " + str(i))
        self.assertEqual(len(chat.history), 12)
        for _ in range(5):
            chat.send("x" * 2000)
        self.assertLessEqual(sum(len(m["content"]) for m in chat.history), 6000)
        self.assertEqual(chat.history[0]["role"], "user")
        with self.assertRaises(ValueError):
            chat.send("x" * 2001)
        chat.clear()
        self.assertEqual(chat.history, [])

    def test_configuration_rejects_cloud_model(self):
        with self.assertRaises(ValueError):
            OllamaClient(model="some-cloud-model")
        with self.assertRaises(ValueError):
            OllamaClient(port=0)


if __name__ == "__main__":
    unittest.main()
