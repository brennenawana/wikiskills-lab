#!/usr/bin/env python3
"""Observability probes — miniature tests that PROVE a recorder works.

A requirement from steps/2-observe/requirements.md counts as met only when a
probe has demonstrated it on this machine. This tool runs those probes.

  python3 probe.py proxy    # prove the recording proxy end to end
                            #   (spawns its own fake upstream; no real
                            #    credentials, no network, no spend)
  python3 probe.py hook     # prove the Claude Code hook script
  python3 probe.py replay   # prove replay mode: fixtures served, misses
                            #   fail closed, no upstream needed
  python3 probe.py ledger --file PATH
                            # validate any ledger file a third-party
                            #   recorder claims to write (O4/O5/O6 only)

Exit code 0 = every probe passed. Anything else = the recorder is not ready;
do not start a real observed session with it.

Standard library only.
"""

import argparse
import http.client
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

FAKE_HEADER_SECRET = "sk-PROBE-FAKE-HEADER-SECRET-0001"
FAKE_BODY_SECRET = "ghp_PROBEFAKEBODYSECRET000000001"

RESULTS = []


def check(req_id, name, ok, note=""):
    RESULTS.append((req_id, name, bool(ok), note))
    mark = "PASS" if ok else "FAIL"
    line = "  [%s] %-3s %s" % (mark, req_id, name)
    if note and not ok:
        line += "  -- " + note
    print(line)


def summary():
    failed = [r for r in RESULTS if not r[2]]
    print()
    if failed:
        print("RESULT: %d of %d probes FAILED. This recorder is not ready."
              % (len(failed), len(RESULTS)))
        print("Fix the failures and run the probe again. Do not start a real")
        print("observed session until every probe passes.")
        return 1
    print("RESULT: all %d probes passed." % len(RESULTS))
    return 0


# ---------------------------------------------------------------- fake API

class FakeUpstream(http.server.BaseHTTPRequestHandler):
    """Answers like an OpenAI- or Anthropic-style API, with known numbers."""

    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def _send(self, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(length)
        if self.path.endswith("/chat/completions"):
            self._send({"id": "probe", "model": "probe-model",
                        "choices": [{"message": {"role": "assistant",
                                                 "content": "ok"}}],
                        "usage": {"prompt_tokens": 12,
                                  "completion_tokens": 7}})
        elif self.path.endswith("/messages"):
            self._send({"id": "probe", "model": "probe-model-anthropic",
                        "content": [{"type": "text", "text": "ok"}],
                        "usage": {"input_tokens": 30, "output_tokens": 9,
                                  "cache_read_input_tokens": 4}})
        elif self.path.endswith("/stream"):
            events = (
                b'data: {"model":"probe-model","choices":[{"delta":'
                b'{"content":"ok"}}]}\n\n'
                b'data: {"usage":{"prompt_tokens":5,"completion_tokens":3}}'
                b'\n\ndata: [DONE]\n\n')
            self._send(events, ctype="text/event-stream")
        else:
            self._send({"echo": self.path})

    def do_GET(self):
        self._send({"ticket": "PROJ-1", "fields": {"summary": "probe"}})


def start_fake_upstream():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeUpstream)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def call(port, method, path, body=None, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    payload = json.dumps(body).encode() if body is not None else None
    conn.request(method, path, body=payload, headers=headers or {})
    resp = conn.getresponse()
    data = resp.read()
    conn.close()
    return resp.status, data


def read_ledger(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


# ------------------------------------------------------------- proxy probe

def probe_proxy():
    import proxy as proxy_mod

    print("Probing the recording proxy (fake upstream, no real secrets):")
    tmp = tempfile.mkdtemp(prefix="wsl-probe-")
    ledger = os.path.join(tmp, "model_calls.jsonl")
    capture = os.path.join(tmp, "capture")

    upstream = start_fake_upstream()
    up_port = upstream.server_address[1]

    ready = threading.Event()
    threading.Thread(
        target=proxy_mod.serve,
        args=("http://127.0.0.1:%d" % up_port, 0, ledger, capture,
              "probe", ready),
        daemon=True).start()
    ready.wait(5)
    px_port = ready.server.server_address[1]

    secret_headers = {"Content-Type": "application/json",
                      "Authorization": "Bearer " + FAKE_HEADER_SECRET}
    body = {"model": "probe-model", "messages": [
        {"role": "user", "content": "hello " + FAKE_BODY_SECRET}]}

    # O1: every call -> exactly one row
    call(px_port, "POST", "/v1/chat/completions", body, secret_headers)
    call(px_port, "POST", "/v1/messages", body, secret_headers)
    call(px_port, "GET", "/rest/api/2/issue/PROJ-1",
         headers={"Authorization": "Bearer " + FAKE_HEADER_SECRET})
    time.sleep(0.2)
    rows = read_ledger(ledger)
    check("O1", "one ledger row per call, none missing", len(rows) == 3,
          "expected 3 rows, found %d" % len(rows))

    # O2: token usage parsed correctly, both API styles
    oai = rows[0] if rows else {}
    anth = rows[1] if len(rows) > 1 else {}
    check("O2", "OpenAI-style tokens parsed",
          oai.get("tokens_in") == 12 and oai.get("tokens_out") == 7,
          "got %s/%s" % (oai.get("tokens_in"), oai.get("tokens_out")))
    check("O2", "Anthropic-style tokens + cache parsed",
          anth.get("tokens_in") == 30 and anth.get("tokens_out") == 9
          and anth.get("cache_read") == 4,
          "got %s/%s/%s" % (anth.get("tokens_in"), anth.get("tokens_out"),
                            anth.get("cache_read")))
    check("O2", "model name recorded",
          oai.get("model") == "probe-model", str(oai.get("model")))

    # O2 on streams: usage present in the stream is found
    call(px_port, "POST", "/v1/stream", body, secret_headers)
    time.sleep(0.2)
    rows = read_ledger(ledger)
    sse = rows[-1]
    check("O2", "streamed (SSE) usage parsed",
          sse.get("stream") is True and sse.get("tokens_in") == 5
          and sse.get("tokens_out") == 3,
          "got stream=%s %s/%s" % (sse.get("stream"), sse.get("tokens_in"),
                                   sse.get("tokens_out")))

    # O3: byte-identical passthrough (direct vs via proxy)
    _, direct = call(up_port, "POST", "/v1/chat/completions", body,
                     {"Content-Type": "application/json"})
    _, proxied = call(px_port, "POST", "/v1/chat/completions", body,
                      {"Content-Type": "application/json"})
    check("O3", "response through proxy is byte-identical",
          direct == proxied)

    # O4: durable + append-only (reread from disk; earlier rows unchanged)
    first_before = read_ledger(ledger)[0]
    size_before = os.path.getsize(ledger)
    call(px_port, "GET", "/rest/api/2/issue/PROJ-2")
    time.sleep(0.2)
    check("O4", "ledger grows by append; earlier rows untouched",
          os.path.getsize(ledger) > size_before
          and read_ledger(ledger)[0] == first_before)

    # O5: timestamps present, ordered; durations sane
    rows = read_ledger(ledger)
    ts_ok = all(r.get("ts") for r in rows) and \
        all(rows[i]["ts"] <= rows[i + 1]["ts"] for i in range(len(rows) - 1))
    check("O5", "every row timestamped (UTC) and in order",
          ts_ok and all(r.get("dur_ms", 0) >= 0 for r in rows))

    # O6: the fake secrets appear nowhere on disk
    blobs = [open(ledger, encoding="utf-8").read()]
    for fn in os.listdir(capture):
        blobs.append(open(os.path.join(capture, fn), encoding="utf-8").read())
    leaked = any(FAKE_HEADER_SECRET in b or FAKE_BODY_SECRET in b
                 for b in blobs)
    check("O6", "secrets scrubbed from ledger AND captures", not leaked)

    # O8: captures exist and hold usable request/response pairs
    caps = sorted(os.listdir(capture))
    ok8 = False
    if caps:
        cap0 = json.load(open(os.path.join(capture, caps[0]),
                              encoding="utf-8"))
        ok8 = ("request" in cap0 and "response" in cap0
               and cap0["response"]["body"]["data"])
    check("O8", "full scrubbed captures written (replay raw material)", ok8)

    upstream.shutdown()
    return summary()


# ------------------------------------------------------------ replay probe

def probe_replay():
    import proxy as proxy_mod

    print("Probing replay mode (record, kill the upstream, replay):")
    tmp = tempfile.mkdtemp(prefix="wsl-probe-")
    capture = os.path.join(tmp, "capture")

    # 1. Record two real exchanges.
    upstream = start_fake_upstream()
    up_port = upstream.server_address[1]
    ready = threading.Event()
    threading.Thread(
        target=proxy_mod.serve,
        args=("http://127.0.0.1:%d" % up_port, 0,
              os.path.join(tmp, "record.jsonl"), capture, "rec", ready),
        daemon=True).start()
    ready.wait(5)
    rec_port = ready.server.server_address[1]
    _, recorded = call(rec_port, "GET", "/rest/api/2/issue/PROJ-1")
    call(rec_port, "POST", "/v1/chat/completions",
         {"model": "probe-model", "messages": []},
         {"Content-Type": "application/json"})
    time.sleep(0.2)
    ready.server.shutdown()
    upstream.shutdown()          # the live world is now GONE

    # 2. Replay from the captures alone.
    replay_ledger = os.path.join(tmp, "replay.jsonl")
    ready2 = threading.Event()
    threading.Thread(
        target=proxy_mod.serve,
        args=(None, 0, replay_ledger, None, "replay", ready2),
        kwargs={"replay_dir": capture}, daemon=True).start()
    ready2.wait(5)
    rp_port = ready2.server.server_address[1]

    status, replayed = call(rp_port, "GET", "/rest/api/2/issue/PROJ-1")
    check("R1", "recorded exchange served from fixtures (no upstream)",
          status == 200 and json.loads(replayed) == json.loads(recorded))
    status2, body2 = call(rp_port, "GET", "/rest/api/2/issue/NOPE-999")
    check("R2", "unmatched request FAILS CLOSED (503 replay-miss)",
          status2 == 503 and b"replay-miss" in body2)
    time.sleep(0.2)
    rows = read_ledger(replay_ledger)
    check("R3", "replay ledger records hits and the miss",
          len(rows) == 2 and rows[0].get("replayed") is True
          and rows[1].get("error") == "replay-miss")
    ready2.server.shutdown()
    return summary()


# -------------------------------------------------------------- hook probe

def probe_hook():
    print("Probing the Claude Code hook script:")
    tmp = tempfile.mkdtemp(prefix="wsl-probe-")
    ledger = os.path.join(tmp, "actions.jsonl")
    script = os.path.join(HERE, "hooks", "ledger_hook.py")

    events = [
        {"hook_event_name": "PreToolUse", "session_id": "probe",
         "tool_name": "Bash",
         "tool_input": {"command": "curl -H 'Authorization: Bearer %s'"
                        % FAKE_HEADER_SECRET}},
        {"hook_event_name": "PostToolUse", "session_id": "probe",
         "tool_name": "Read",
         "tool_input": {"file_path": "/tmp/x"},
         "tool_response": {"ok": True}},
        {"hook_event_name": "Stop", "session_id": "probe"},
    ]
    codes = []
    for ev in events:
        proc = subprocess.run(
            [sys.executable, script, ledger],
            input=json.dumps(ev).encode(), capture_output=True, timeout=20)
        codes.append(proc.returncode)

    rows = read_ledger(ledger) if os.path.exists(ledger) else []
    check("O1", "one row per hook event", len(rows) == 3,
          "expected 3, found %d" % len(rows))
    check("O5", "rows timestamped and typed",
          all(r.get("ts") and r.get("event") for r in rows))
    check("O6", "secrets scrubbed from action rows",
          FAKE_HEADER_SECRET not in
          (open(ledger, encoding="utf-8").read() if rows else ""))
    check("O3", "hook never blocks the agent (exit 0, even on garbage)",
          all(c == 0 for c in codes) and subprocess.run(
              [sys.executable, script, ledger], input=b"not json",
              capture_output=True, timeout=20).returncode == 0)
    return summary()


# ------------------------------------------------------------ ledger probe

def probe_ledger(path):
    print("Validating third-party ledger file: %s" % path)
    ok_parse, rows = True, []
    try:
        rows = read_ledger(path)
    except (OSError, ValueError) as exc:
        check("O4", "file exists and every line is valid JSON", False,
              str(exc))
        return summary()
    check("O4", "file exists and every line is valid JSON",
          ok_parse and len(rows) > 0, "no rows" if not rows else "")
    check("O5", "every row has a UTC timestamp, rows in order",
          all(r.get("ts") for r in rows) and
          all(rows[i]["ts"] <= rows[i + 1]["ts"]
              for i in range(len(rows) - 1)))
    text = open(path, encoding="utf-8").read()
    suspicious = any(marker in text for marker in
                     ("sk-", "ghp_", "github_pat_", "Bearer "))
    check("O6", "no obvious secret markers in the file", not suspicious,
          "found a marker; inspect and fix scrubbing")
    print()
    print("Note: a passing file proves format only. O1 (completeness), O2")
    print("(tokens), and O3 (no behavior change) still need the live canary")
    print("check in steps/2-observe/probes.md before the tool is accepted.")
    return summary()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=["proxy", "hook", "replay", "ledger"])
    ap.add_argument("--file", help="ledger file (mode: ledger)")
    args = ap.parse_args()
    if args.mode == "proxy":
        sys.exit(probe_proxy())
    if args.mode == "hook":
        sys.exit(probe_hook())
    if args.mode == "replay":
        sys.exit(probe_replay())
    if not args.file:
        ap.error("--file is required for mode 'ledger'")
    sys.exit(probe_ledger(args.file))


if __name__ == "__main__":
    main()
