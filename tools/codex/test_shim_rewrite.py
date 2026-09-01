#!/usr/bin/env python3
"""
Test suite for minimax_reasoning_shim_v3.py.

Exercises the actual implementation of rewrite_json_body() and the
Handler health endpoint over real HTTP.

Cases:
  A. target MiniMax + native built-in web_search type -> removed
  B. ordinary function named web_search (Responses API shape) -> preserved
  C. nested ordinary function.name=web_search -> preserved
  D. ordinary non-web function -> preserved
  E. non-target request -> unchanged
  F. reasoning/reasoning_effort/reasoning_summary -> removed
  G. native web-search tool_choice -> auto
  H. GET /__pi_minimax_shim_health returns exact PI_MINIMAX_SHIM_V3_OK
  I. health request is NOT forwarded upstream
  J. normal non-health request follows forwarding path
  K. ordinary function tool_choice (type=function, name=web_search) -> preserved
"""

import http.client
import json
import socket
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO

# Import the shim module under test
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from minimax_reasoning_shim_v3 import (
    Handler,
    LISTEN_HOST,
    LISTEN_PORT,
    UPSTREAM_HOST,
    UPSTREAM_PORT,
    TARGET_MODEL,
    rewrite_json_body,
)


# ---------------------------------------------------------------------------
# A-G: rewrite_json_body unit tests (direct function exercise)
# ---------------------------------------------------------------------------

def _build_request(body_dict):
    """Build raw request bytes and return them."""
    raw = json.dumps(body_dict, separators=(",", ":")).encode("utf-8")
    return raw


class TestRewriteJsonBody(unittest.TestCase):
    """Cases A through K: exercise rewrite_json_body directly."""

    # A. target MiniMax + native built-in web_search type -> removed
    def test_A_native_web_search_removed(self):
        body = _build_request({
            "model": TARGET_MODEL,
            "tools": [{"type": "web_search", "name": "codex_web_search"}],
        })
        result, changes = rewrite_json_body(body)
        obj = json.loads(result)
        self.assertEqual(obj["tools"], [],
                         "native web_search tool must be removed")
        self.assertTrue(any("web_search" in c for c in changes),
                        "changes should mention web_search removal")

    # B. ordinary function named web_search (Responses API shape) -> preserved
    def test_B_ordinary_function_web_search_preserved(self):
        body = _build_request({
            "model": TARGET_MODEL,
            "tools": [{
                "type": "function",
                "name": "web_search",
                "description": "search the web",
                "parameters": {"type": "object", "properties": {}},
            }],
        })
        result, changes = rewrite_json_body(body)
        obj = json.loads(result)
        self.assertEqual(len(obj["tools"]), 1,
                         "ordinary function named web_search must be preserved")
        self.assertEqual(obj["tools"][0]["type"], "function")
        self.assertEqual(obj["tools"][0]["name"], "web_search")
    # C. nested ordinary function.name=web_search -> preserved
    def test_C_nested_function_web_search_preserved(self):
        body = _build_request({
            "model": TARGET_MODEL,
            "tools": [{
                "type": "function",
                "function": {
                    "name": "web_search",
                    "input_schema": {"type": "object", "properties": {"q": {"type": "string"}}},
                },
            }],
        })
        result, changes = rewrite_json_body(body)
        obj = json.loads(result)
        self.assertEqual(len(obj["tools"]), 1,
                         "nested function.name=web_search must be preserved")
        func_name = obj["tools"][0]["function"]["name"]
        self.assertEqual(func_name, "web_search")

    # D. ordinary non-web function -> preserved
    def test_D_ordinary_non_web_function_preserved(self):
        body = _build_request({
            "model": TARGET_MODEL,
            "tools": [{
                "type": "function",
                "function": {
                    "name": "calculate_price",
                    "input_schema": {"type": "object", "properties": {}},
                },
            }],
        })
        result, changes = rewrite_json_body(body)
        obj = json.loads(result)
        self.assertEqual(len(obj["tools"]), 1,
                         "ordinary non-web function must be preserved")
        self.assertEqual(obj["tools"][0]["function"]["name"], "calculate_price")

    # E. non-target request -> unchanged
    def test_E_non_target_model_unchanged(self):
        body = _build_request({
            "model": "gpt-4o",
            "tools": [{"type": "web_search", "name": "codex_web_search"}],
            "reasoning": {"effort": "high"},
            "reasoning_effort": "high",
        })
        result, changes = rewrite_json_body(body)
        self.assertEqual(result, body,
                         "non-target model request must be byte-identical")
        self.assertEqual(changes, [], "no changes for non-target model")

    # F. reasoning/reasoning_effort/reasoning_summary -> removed
    def test_F_reasoning_keys_removed(self):
        body = _build_request({
            "model": TARGET_MODEL,
            "reasoning": {"effort": "high"},
            "reasoning_effort": "high",
            "reasoning_summary": "summarize thinking",
        })
        result, changes = rewrite_json_body(body)
        obj = json.loads(result)
        self.assertNotIn("reasoning", obj, "reasoning must be removed")
        self.assertNotIn("reasoning_effort", obj, "reasoning_effort must be removed")
        self.assertNotIn("reasoning_summary", obj, "reasoning_summary must be removed")
        self.assertTrue(len(changes) >= 3,
                        "should record removal of each reasoning key")

    # G. native web-search tool_choice -> auto
    def test_G_web_search_tool_choice_to_auto(self):
        body = _build_request({
            "model": TARGET_MODEL,
            "tool_choice": {"type": "web_search", "name": "codex_web_search"},
        })
        result, changes = rewrite_json_body(body)
        obj = json.loads(result)
        self.assertEqual(obj["tool_choice"], "auto",
                         "web_search tool_choice must become auto")
        self.assertTrue(any("tool_choice" in c for c in changes),
                        "changes should mention tool_choice change")

    # K. ordinary function tool_choice (type=function, name=web_search) -> preserved
    def test_K_function_tool_choice_preserved(self):
        body = _build_request({
            "model": TARGET_MODEL,
            "tool_choice": {
                "type": "function",
                "name": "web_search",
            },
        })
        result, changes = rewrite_json_body(body)
        obj = json.loads(result)
        self.assertIn("tool_choice", obj,
                       "ordinary function tool_choice must remain present")
        tc = obj["tool_choice"]
        self.assertNotEqual(tc, "auto",
                            "ordinary function tool_choice must NOT become auto")
        self.assertEqual(tc["type"], "function",
                         "tool_choice type must remain function")
        self.assertEqual(tc["name"], "web_search",
                         "tool_choice name must remain web_search")
        self.assertFalse(any("tool_choice" in c for c in changes),
                         "no tool_choice change should be recorded")

# ---------------------------------------------------------------------------
# H-J: Handler health endpoint tests (real HTTP exercise)
# ---------------------------------------------------------------------------

class _FakeUpstreamHandler(BaseHTTPRequestHandler):
    """Minimal upstream that records every request it receives."""
    received_requests = []

    def log_message(self, fmt, *args):
        pass  # silence

    def do_GET(self):
        self.__class__.received_requests.append(("GET", self.path))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        body = b'{"models":[]}'
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b""
        self.__class__.received_requests.append(("POST", self.path, raw))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        body = b'{"id":"resp","choices":[]}'
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _find_free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestHandlerHealth(unittest.TestCase):
    """Cases H through J: exercise the Handler over real HTTP."""

    @classmethod
    def setUpClass(cls):
        _FakeUpstreamHandler.received_requests = []
        cls.upstream_port = _find_free_port()
        cls.shim_port = _find_free_port()

        # Start fake upstream
        cls._upstream = HTTPServer(("127.0.0.1", cls.upstream_port), _FakeUpstreamHandler)
        cls._upstream_thread = threading.Thread(target=cls._upstream.serve_forever, daemon=True)
        cls._upstream_thread.start()

        # Monkey-patch the shim to use our test ports
        import minimax_reasoning_shim_v3 as shim_mod
        cls._orig_upstream_host = shim_mod.UPSTREAM_HOST
        cls._orig_upstream_port = shim_mod.UPSTREAM_PORT
        cls._orig_listen_host = shim_mod.LISTEN_HOST
        cls._orig_listen_port = shim_mod.LISTEN_PORT

        shim_mod.UPSTREAM_HOST = "127.0.0.1"
        shim_mod.UPSTREAM_PORT = cls.upstream_port
        shim_mod.LISTEN_HOST = "127.0.0.1"
        shim_mod.LISTEN_PORT = cls.shim_port

        # Rebuild Handler class with patched module so it sees new constants
        # The Handler uses the module-level constants at import time for defaults,
        # but the server binding uses the passed (host, port).
        cls._shim = HTTPServer(("127.0.0.1", cls.shim_port), Handler)
        cls._shim_thread = threading.Thread(target=cls._shim.serve_forever, daemon=True)
        cls._shim_thread.start()

        # Wait for shim to be ready
        for _ in range(20):
            try:
                c = http.client.HTTPConnection("127.0.0.1", cls.shim_port, timeout=1)
                c.request("GET", "/__pi_minimax_shim_health")
                r = c.getresponse()
                r.read()
                c.close()
                break
            except Exception:
                time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        import minimax_reasoning_shim_v3 as shim_mod
        shim_mod.UPSTREAM_HOST = cls._orig_upstream_host
        shim_mod.UPSTREAM_PORT = cls._orig_upstream_port
        shim_mod.LISTEN_HOST = cls._orig_listen_host
        shim_mod.LISTEN_PORT = cls._orig_listen_port

        cls._shim.shutdown()
        cls._upstream.shutdown()

    # H. GET /__pi_minimax_shim_health returns exact PI_MINIMAX_SHIM_V3_OK
    def test_H_health_returns_exact_marker(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.__class__.shim_port, timeout=5)
        conn.request("GET", "/__pi_minimax_shim_health")
        resp = conn.getresponse()
        body = resp.read().decode("utf-8").strip()
        conn.close()
        self.assertEqual(resp.status, 200)
        self.assertEqual(body, "PI_MINIMAX_SHIM_V3_OK",
                         "health endpoint must return exact marker")

    # I. health request is NOT forwarded upstream
    def test_I_health_not_forwarded_upstream(self):
        # Clear upstream request log
        _FakeUpstreamHandler.received_requests = []
        conn = http.client.HTTPConnection("127.0.0.1", self.__class__.shim_port, timeout=5)
        conn.request("GET", "/__pi_minimax_shim_health")
        resp = conn.getresponse()
        resp.read()
        conn.close()
        # Give a moment for any forwarding to happen
        time.sleep(0.2)
        health_forwards = [r for r in _FakeUpstreamHandler.received_requests
                           if "__pi_minimax_shim_health" in r[1]]
        self.assertEqual(len(health_forwards), 0,
                         "health request must NOT be forwarded upstream")

    # J. normal non-health request follows forwarding path
    def test_J_normal_request_forwards(self):
        _FakeUpstreamHandler.received_requests = []
        payload = json.dumps({"model": "some-model", "messages": []}).encode()
        conn = http.client.HTTPConnection("127.0.0.1", self.__class__.shim_port, timeout=5)
        conn.request("POST", "/v1/chat/completions", body=payload,
                     headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        resp.read()
        conn.close()
        time.sleep(0.2)
        forwarded = [r for r in _FakeUpstreamHandler.received_requests
                     if "chat/completions" in r[1]]
        self.assertTrue(len(forwarded) >= 1,
                        "normal requests must be forwarded to upstream")


if __name__ == "__main__":
    unittest.main()
