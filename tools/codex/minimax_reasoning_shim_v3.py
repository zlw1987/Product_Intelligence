#!/usr/bin/env python3
"""
Temporary Codex -> LiteLLM compatibility shim, v3.

Listens on 127.0.0.1:18081 and forwards to 127.0.0.1:18080.

ONLY for model == "minimax-m2.7-thinking":
  1) remove top-level OpenAI Responses reasoning metadata:
       - reasoning
       - reasoning_effort
       - reasoning_summary
  2) remove Codex/OpenAI built-in web-search tools that the Anthropic/vLLM
     endpoint rejects because they are not ordinary tools with input_schema.

All ordinary function tools are preserved.

No persistent settings are changed.
"""

import http.client
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 18081
UPSTREAM_HOST = "127.0.0.1"
UPSTREAM_PORT = 18080
TARGET_MODEL = "minimax-m2.7-thinking"

HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host", "content-length",
}

REMOVE_REASONING_KEYS = ("reasoning", "reasoning_effort", "reasoning_summary")


def is_native_web_search_tool(tool):
    """
    Return True ONLY for native built-in web-search tools.
    
    Native web-search tools have:
      - type starting with "web_search" (e.g., "web_search", "web_search_2024")
      - NO "function" key (they are not ordinary function tools)
    
    Ordinary function tools named "web_search" are preserved because they
    have a "function" key with input_schema.
    """
    if not isinstance(tool, dict):
        return False

    t = str(tool.get("type", "")).lower()
    name = str(tool.get("name", "")).lower()

    # Native web-search tools have type starting with "web_search"
    # and do NOT have a "function" key (they are not ordinary functions)
    if t.startswith("web_search"):
        if "function" not in tool:
            return True

    return False


def rewrite_json_body(body: bytes):
    changes = []

    if not body:
        return body, changes

    try:
        obj = json.loads(body.decode("utf-8"))
    except Exception:
        return body, changes

    if not isinstance(obj, dict) or obj.get("model") != TARGET_MODEL:
        return body, changes

    for key in REMOVE_REASONING_KEYS:
        if key in obj:
            value = obj.pop(key)
            if key == "reasoning" and isinstance(value, dict):
                changes.append(f"removed reasoning({','.join(value.keys())})")
            else:
                changes.append(f"removed {key}")

    tools = obj.get("tools")
    if isinstance(tools, list):
        kept = []
        removed_tools = []

        for tool in tools:
            if is_native_web_search_tool(tool):
                removed_tools.append({
                    "type": tool.get("type"),
                    "name": tool.get("name")
                })
            else:
                kept.append(tool)

        if removed_tools:
            obj["tools"] = kept
            changes.append(
                "removed web_search tool(s): " +
                ", ".join(
                    f"type={x.get('type')!r},name={x.get('name')!r}"
                    for x in removed_tools
                )
            )

    # If an explicit tool_choice pointed at a native built-in web-search
    # tool (type starts with "web_search"), fall back to auto.
    # Ordinary function tool-choices (type="function") must be preserved
    # even when the function is named "web_search".
    tc = obj.get("tool_choice")
    if isinstance(tc, dict):
        tc_type = str(tc.get("type", "")).lower()
        if tc_type.startswith("web_search"):
            obj["tool_choice"] = "auto"
            changes.append("changed web_search tool_choice to auto")

    new_body = json.dumps(
        obj, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")

    return new_body, changes


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        print("[shim-v3] " + (fmt % args), flush=True)

    def _handle(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length) if length else b""

        changes = []
        if body and "application/json" in self.headers.get("Content-Type", "").lower():
            body, changes = rewrite_json_body(body)

        if changes:
            print(
                f"[shim-v3] {self.command} {self.path} "
                f"model={TARGET_MODEL}",
                flush=True
            )
            for change in changes:
                print(f"[shim-v3]   {change}", flush=True)
        else:
            print(f"[shim-v3] {self.command} {self.path} passthrough", flush=True)

        headers = {
            k: v for k, v in self.headers.items()
            if k.lower() not in HOP_BY_HOP
        }
        if body:
            headers["Content-Length"] = str(len(body))

        conn = http.client.HTTPConnection(
            UPSTREAM_HOST, UPSTREAM_PORT, timeout=600
        )

        try:
            conn.request(
                self.command,
                self.path,
                body=body if body else None,
                headers=headers,
            )
            resp = conn.getresponse()

            self.send_response(resp.status, resp.reason)

            content_type = (resp.getheader("Content-Type") or "").lower()
            content_length = resp.getheader("Content-Length")
            is_sse = "text/event-stream" in content_type
            is_chunked = (
                (resp.getheader("Transfer-Encoding") or "").lower() == "chunked"
            )

            for k, v in resp.getheaders():
                lk = k.lower()
                if lk in HOP_BY_HOP or lk == "content-length":
                    continue
                self.send_header(k, v)

            if content_length and not is_sse and not is_chunked:
                self.send_header("Content-Length", content_length)
            else:
                self.send_header("Connection", "close")
                self.close_connection = True

            self.end_headers()

            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()

        except Exception as exc:
            payload = json.dumps({
                "error": {"message": f"temporary shim upstream error: {exc}"}
            }).encode("utf-8")
            try:
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(payload)
                self.close_connection = True
            except Exception:
                pass
        finally:
            conn.close()

    def _handle_health(self):
        """Handle health check endpoint - never forwarded upstream."""
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len("PI_MINIMAX_SHIM_V3_OK")))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(b"PI_MINIMAX_SHIM_V3_OK")
        self.close_connection = True

    do_GET = _handle
    do_POST = _handle
    do_PUT = _handle
    do_PATCH = _handle
    do_DELETE = _handle
    do_OPTIONS = _handle

    def do_HEAD(self):
        if self.path == "/__pi_minimax_shim_health":
            self._handle_health()
        else:
            self._handle()

    def do_GET(self):
        if self.path == "/__pi_minimax_shim_health":
            self._handle_health()
        else:
            self._handle()


if __name__ == "__main__":
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), Handler)
    print(
        f"[shim-v3] listening http://{LISTEN_HOST}:{LISTEN_PORT} "
        f"-> http://{UPSTREAM_HOST}:{UPSTREAM_PORT}"
    )
    print(
        "[shim-v3] MiniMax Thinking only: removes reasoning metadata "
        "and incompatible built-in web_search tool"
    )
    print("[shim-v3] Ctrl+C to stop; no persistent settings are changed")
    print("[shim-v3] Health endpoint: GET /__pi_minimax_shim_health")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[shim-v3] stopped")
    finally:
        server.server_close()
