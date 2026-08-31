#!/usr/bin/env python3
"""Recording proxy — record mode.

Sits between a client (your agent, harness, or pipeline) and ONE upstream
HTTP API. Forwards every request unchanged, streams the response back, and
writes one ledger row per exchange. Optionally captures full (scrubbed)
request/response bodies as replay raw material.

Standard library only. Runs the same on macOS, Linux, and Windows.

Usage:
  python3 proxy.py --upstream https://api.example.com \
      --port 8788 --ledger workspace/ledgers/model_calls.jsonl \
      [--name my-endpoint] [--capture workspace/ledgers/capture]

Then point the client's base URL at http://127.0.0.1:8788 instead of the
upstream. Run one proxy per upstream (one for the model, one for the
tracker, ...), each with its own --name, --port, and ledger.
"""

import argparse
import base64
import datetime
import http.client
import http.server
import json
import os
import re
import ssl
import sys
import threading
import time
import urllib.parse

LEDGER_VERSION = 1
PARSE_BUFFER_CAP = 8 * 1024 * 1024  # parse/capture at most 8 MB per body

HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host",
    "content-length",  # recomputed
}
SENSITIVE_HEADERS = {
    "authorization", "proxy-authorization", "x-api-key", "api-key",
    "cookie", "set-cookie", "x-goog-api-key", "openai-api-key",
    "x-auth-token", "private-token",
}
SECRET_PATTERNS = [
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=\-]{8,}"), "Bearer [SCRUBBED]"),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{8,}"), "[SCRUBBED]"),
    (re.compile(r"\bghp_[A-Za-z0-9]{20,}"), "[SCRUBBED]"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"), "[SCRUBBED]"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}"), "[SCRUBBED]"),
    (re.compile(
        r'(?i)("(?:api[-_]?key|apikey|token|secret|password|authorization)"'
        r'\s*:\s*")[^"]{4,}(")'), r"\1[SCRUBBED]\2"),
]


def scrub_text(text):
    for pat, rep in SECRET_PATTERNS:
        text = pat.sub(rep, text)
    return text


def scrub_headers(headers):
    out = {}
    for k, v in headers.items():
        if k.lower() in SENSITIVE_HEADERS:
            out[k] = "[SCRUBBED]"
        else:
            out[k] = scrub_text(v)
    return out


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(
        timespec="milliseconds")


def parse_usage(body_bytes, is_sse):
    """Best-effort token usage from an OpenAI- or Anthropic-style response.

    Returns (model, tokens_in, tokens_out, cache_read, cache_write, note).
    Every usage object seen is folded in; for cumulative stream counters the
    maximum wins, so partial deltas never undercount the final figure.
    """
    text = body_bytes[:PARSE_BUFFER_CAP].decode("utf-8", "replace")
    events = []
    if is_sse:
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                payload = line[5:].strip()
                if payload and payload != "[DONE]":
                    try:
                        events.append(json.loads(payload))
                    except ValueError:
                        pass
    else:
        try:
            events.append(json.loads(text))
        except ValueError:
            return None, None, None, None, None, "unparsed-body"

    model = None
    fields = {"in": 0, "out": 0, "cr": 0, "cw": 0}
    saw_usage = False

    def fold(usage):
        nonlocal saw_usage
        if not isinstance(usage, dict):
            return
        saw_usage = True
        mapping = {
            "in": ("input_tokens", "prompt_tokens"),
            "out": ("output_tokens", "completion_tokens"),
            "cr": ("cache_read_input_tokens", "cached_tokens"),
            "cw": ("cache_creation_input_tokens",),
        }
        for key, names in mapping.items():
            for name in names:
                val = usage.get(name)
                if isinstance(val, (int, float)):
                    fields[key] = max(fields[key], int(val))

    for ev in events:
        if not isinstance(ev, dict):
            continue
        model = ev.get("model") or (
            ev.get("message", {}).get("model")
            if isinstance(ev.get("message"), dict) else None) or model
        fold(ev.get("usage"))
        if isinstance(ev.get("message"), dict):
            fold(ev["message"].get("usage"))

    if not saw_usage:
        return model, None, None, None, None, "no-usage-in-response"
    return (model, fields["in"], fields["out"], fields["cr"], fields["cw"],
            None)


class Recorder:
    """Serialized writer for the ledger and the capture directory."""

    def __init__(self, ledger_path, capture_dir, name):
        self.ledger_path = ledger_path
        self.capture_dir = capture_dir
        self.name = name
        self.lock = threading.Lock()
        self.seq = 0
        os.makedirs(os.path.dirname(os.path.abspath(ledger_path)),
                    exist_ok=True)
        if capture_dir:
            os.makedirs(capture_dir, exist_ok=True)

    def record(self, row, req_headers, req_body, resp_headers, resp_body):
        with self.lock:
            self.seq += 1
            row["seq"] = self.seq
            with open(self.ledger_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            if self.capture_dir:
                self._capture(row, req_headers, req_body, resp_headers,
                              resp_body)

    @staticmethod
    def _body_field(body):
        text = body[:PARSE_BUFFER_CAP].decode("utf-8", "replace")
        if "�" in text and len(body):
            return {"encoding": "base64",
                    "data": base64.b64encode(body[:PARSE_BUFFER_CAP])
                    .decode("ascii")}
        return {"encoding": "text", "data": scrub_text(text)}

    def _capture(self, row, req_headers, req_body, resp_headers, resp_body):
        safe_path = re.sub(r"[^A-Za-z0-9._-]+", "_", row["path"])[:80]
        fname = "%06d_%s_%s.json" % (row["seq"], row["method"], safe_path)
        record = {
            "v": LEDGER_VERSION, "ts": row["ts"], "seq": row["seq"],
            "proxy": self.name,
            "request": {"method": row["method"], "path": row["path"],
                        "headers": scrub_headers(dict(req_headers)),
                        "body": self._body_field(req_body)},
            "response": {"status": row["status"],
                         "headers": scrub_headers(dict(resp_headers)),
                         "body": self._body_field(resp_body)},
        }
        with open(os.path.join(self.capture_dir, fname), "w",
                  encoding="utf-8") as fh:
            json.dump(record, fh, ensure_ascii=False, indent=1)


def make_handler(upstream, recorder):
    parsed = urllib.parse.urlsplit(upstream)
    scheme, netloc = parsed.scheme, parsed.netloc
    base_path = parsed.path.rstrip("/")

    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):  # quiet; the ledger is the log
            pass

        def _forward(self):
            start = time.monotonic()
            length = int(self.headers.get("Content-Length") or 0)
            req_body = self.rfile.read(length) if length else b""

            up_headers = {}
            for k, v in self.headers.items():
                if k.lower() not in HOP_BY_HOP:
                    up_headers[k] = v
            up_headers["Host"] = netloc
            up_headers["Content-Length"] = str(len(req_body))
            up_headers["Connection"] = "close"

            if scheme == "https":
                conn = http.client.HTTPSConnection(
                    netloc, context=ssl.create_default_context(), timeout=600)
            else:
                conn = http.client.HTTPConnection(netloc, timeout=600)

            target = base_path + self.path
            note = None
            try:
                conn.request(self.command, target, body=req_body,
                             headers=up_headers)
                resp = conn.getresponse()
            except OSError as exc:
                self.send_response(502)
                self.send_header("Content-Length", "0")
                self.end_headers()
                recorder.record(
                    {"v": LEDGER_VERSION, "ts": now_iso(),
                     "proxy": recorder.name, "method": self.command,
                     "path": self.path, "status": 502,
                     "dur_ms": int((time.monotonic() - start) * 1000),
                     "req_bytes": len(req_body), "resp_bytes": 0,
                     "error": "upstream-unreachable: %s" % exc},
                    self.headers, req_body, {}, b"")
                return

            resp_headers = dict(resp.getheaders())
            content_type = resp_headers.get("Content-Type", "")
            is_sse = "text/event-stream" in content_type
            declared_len = resp.getheader("Content-Length")

            self.send_response(resp.status)
            for k, v in resp_headers.items():
                if k.lower() not in HOP_BY_HOP:
                    self.send_header(k, v)
            chunked = declared_len is None
            if chunked:
                self.send_header("Transfer-Encoding", "chunked")
            else:
                self.send_header("Content-Length", declared_len)
            self.send_header("Connection", "close")
            self.end_headers()

            buffered = bytearray()
            total = 0
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                total += len(chunk)
                if len(buffered) < PARSE_BUFFER_CAP:
                    buffered.extend(chunk)
                try:
                    if chunked:
                        self.wfile.write(b"%x\r\n" % len(chunk))
                        self.wfile.write(chunk)
                        self.wfile.write(b"\r\n")
                    else:
                        self.wfile.write(chunk)
                    self.wfile.flush()
                except OSError:
                    note = "client-disconnected"
                    break
            if chunked and note is None:
                try:
                    self.wfile.write(b"0\r\n\r\n")
                except OSError:
                    note = "client-disconnected"
            conn.close()

            model, t_in, t_out, c_read, c_write, parse_note = parse_usage(
                bytes(buffered), is_sse)
            row = {
                "v": LEDGER_VERSION, "ts": now_iso(),
                "proxy": recorder.name, "method": self.command,
                "path": self.path, "status": resp.status,
                "dur_ms": int((time.monotonic() - start) * 1000),
                "req_bytes": len(req_body), "resp_bytes": total,
                "stream": is_sse, "model": model,
                "tokens_in": t_in, "tokens_out": t_out,
                "cache_read": c_read, "cache_write": c_write,
            }
            for extra in (note, parse_note):
                if extra:
                    row["note"] = (row.get("note", "") + " " + extra).strip()
            recorder.record(row, self.headers, req_body, resp_headers,
                            bytes(buffered))

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = _forward

    return Handler


def serve(upstream, port, ledger, capture, name, ready_event=None):
    recorder = Recorder(ledger, capture, name)
    handler = make_handler(upstream, recorder)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    if ready_event is not None:
        ready_event.server = server
        ready_event.set()
    print("recording proxy '%s': http://127.0.0.1:%d -> %s"
          % (name, server.server_address[1], upstream), file=sys.stderr)
    print("ledger: %s" % ledger, file=sys.stderr)
    server.serve_forever()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--upstream", required=True,
                    help="base URL to forward to, e.g. https://api.host.com")
    ap.add_argument("--port", type=int, default=8788)
    ap.add_argument("--ledger", required=True,
                    help="JSONL ledger file (appended, never truncated)")
    ap.add_argument("--capture", default=None,
                    help="directory for full scrubbed request/response "
                         "captures (replay raw material)")
    ap.add_argument("--name", default="upstream",
                    help="short name for this endpoint in ledger rows")
    args = ap.parse_args()
    serve(args.upstream, args.port, args.ledger, args.capture, args.name)


if __name__ == "__main__":
    main()
