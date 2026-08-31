#!/usr/bin/env python3
"""First-mile path test — the whole engine, on the local-model path.

Simulates the first kind of user this repository was built for: a
self-hosted model behind an OpenAI-style endpoint, a ticket tracker, and a
pipeline script that connects them. Everything runs against local fakes —
no real model, no credentials, no network, no spend — but every engine
component in the chain is the real one:

  record (two proxies) -> ledgers with tokens + scrubbing
    -> capsule (freeze + verify)
    -> hermetic replay (misses fail closed)
    -> metered baseline through the gateway and suite runner
    -> before/after report plumbing

  python3 scripts/first_mile_test.py

This does NOT replace testing with a real local model — it proves the
plumbing, not the model. Exit 0 = the path works on this machine.
"""

import http.server
import json
import os
import sys
import tempfile
import threading
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ("recorder", "gateway", "budget", "measure", "capsule",
            "report"):
    sys.path.insert(0, os.path.join(REPO, "engine", sub))

import proxy as proxy_mod          # noqa: E402
import capsule as capsule_mod      # noqa: E402
import report as report_mod        # noqa: E402
import runner as runner_mod        # noqa: E402
from gateway import Gateway        # noqa: E402
from meter import Meter            # noqa: E402

FAKE_TOKEN = "sk-FIRSTMILE-FAKE-TOKEN-0001"
RESULTS = []


def check(name, cond, note=""):
    RESULTS.append(bool(cond))
    print("  [%s] %s%s" % ("PASS" if cond else "FAIL", name,
                           ("  -- " + note) if (note and not cond) else ""))


class FakeWorld(http.server.BaseHTTPRequestHandler):
    """One server plays both the local model and the tracker."""

    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):        # the "tracker"
        self._send({"key": self.path.rsplit("/", 1)[-1],
                    "summary": "retries flood the upstream",
                    "comments": ["see linked ticket"],
                    "links": ["ORB-9"]})

    def do_POST(self):       # the "local model"
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        self._send({"model": "local-30b",
                    "choices": [{"message": {"content": "42"}}],
                    "usage": {"prompt_tokens": 400,
                              "completion_tokens": 12}})


def start_proxy(upstream, ledger, capture=None, replay_dir=None,
                name="px"):
    ready = threading.Event()
    threading.Thread(target=proxy_mod.serve,
                     args=(upstream, 0, ledger, capture, name, ready),
                     kwargs={"replay_dir": replay_dir},
                     daemon=True).start()
    ready.wait(5)
    return ready.server


def http_call(port, method, path, body=None, headers=None):
    import http.client
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    payload = json.dumps(body).encode() if body is not None else None
    conn.request(method, path, body=payload, headers=headers or {})
    resp = conn.getresponse()
    data = resp.read()
    conn.close()
    return resp.status, data


def main():
    d = tempfile.mkdtemp(prefix="wsl-firstmile-")
    world = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeWorld)
    threading.Thread(target=world.serve_forever, daemon=True).start()
    wport = world.server_address[1]

    print("Stage 1 — record a 'real' session through the two proxies:")
    model_led = os.path.join(d, "model_calls.jsonl")
    track_led = os.path.join(d, "tracker_calls.jsonl")
    track_cap = os.path.join(d, "tracker_capture")
    px_model = start_proxy("http://127.0.0.1:%d" % wport, model_led,
                           os.path.join(d, "model_capture"), name="model")
    px_track = start_proxy("http://127.0.0.1:%d" % wport, track_led,
                           track_cap, name="tracker")
    mport = px_model.server_address[1]
    tport = px_track.server_address[1]

    # The "pipeline": fetch the ticket, then call the model.
    auth = {"Authorization": "Bearer " + FAKE_TOKEN,
            "Content-Type": "application/json"}
    http_call(tport, "GET", "/rest/api/2/issue/ORB-4127", headers=auth)
    http_call(mport, "POST", "/v1/chat/completions",
              {"model": "local-30b",
               "messages": [{"role": "user", "content": "fix ORB-4127"}]},
              auth)
    time.sleep(0.2)
    rows_m = [json.loads(l) for l in open(model_led) if l.strip()]
    rows_t = [json.loads(l) for l in open(track_led) if l.strip()]
    check("both streams measured (one row each)",
          len(rows_m) == 1 and len(rows_t) == 1)
    check("token usage visible on the model stream",
          rows_m[0].get("tokens_in") == 400
          and rows_m[0].get("tokens_out") == 12)
    blob = open(model_led).read() + open(track_led).read()
    for fn in os.listdir(track_cap):
        blob += open(os.path.join(track_cap, fn)).read()
    check("planted token scrubbed everywhere", FAKE_TOKEN not in blob)
    px_model.shutdown()
    px_track.shutdown()

    print("Stage 2 — freeze the session into a capsule and verify it:")
    cap_dir = os.path.join(d, "capsule")
    capsule_mod.create(cap_dir, "ORB-4127 sample", [],
                       fixtures_dir=track_cap)
    ok, problems = capsule_mod.verify(cap_dir)
    check("capsule created and verified", ok, "; ".join(problems))

    print("Stage 3 — hermetic replay (the live world is gone):")
    world.shutdown()
    rp = start_proxy(None, os.path.join(d, "replay.jsonl"),
                     replay_dir=os.path.join(cap_dir, "fixtures"),
                     name="replay")
    rport = rp.server_address[1]
    status, body = http_call(rport, "GET", "/rest/api/2/issue/ORB-4127")
    check("frozen ticket served from the capsule",
          status == 200 and b"retries flood" in body)
    status2, body2 = http_call(rport, "GET", "/rest/api/2/issue/OTHER-1")
    check("unrecorded request fails closed",
          status2 == 503 and b"replay-miss" in body2)
    rp.shutdown()

    print("Stage 4 — metered baseline through gateway + runner:")
    world2 = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeWorld)
    threading.Thread(target=world2.serve_forever, daemon=True).start()
    suite = {"v": 1, "name": "first-mile", "version": "1",
             "tasks": [
                 {"id": "t1", "instruction": "answer 42",
                  "scorer": {"kind": "exact", "expected": "42"}},
                 {"id": "t2", "instruction": "answer 42",
                  "scorer": {"kind": "token-budget",
                             "max_tokens": 1000}}]}
    caps = {"unit": "tokens", "caps": [
        {"scope": "total", "limit": 5000, "consequence": "stop"}]}
    meter = Meter(os.path.join(d, "spend.jsonl"), caps)
    cfg = {"kind": "openai",
           "base_url": "http://127.0.0.1:%d" % world2.server_address[1],
           "model": "local-30b"}
    summary = runner_mod.run_suite(suite, cfg, meter, "baseline", d, 500,
                                   gateway=Gateway())
    check("baseline measured on the local-model backend",
          summary["n_tasks"] == 2 and summary["mean_score"] == 1.0)
    check("token budget metered (unit: tokens)",
          meter.spent("total") == 2 * 412)
    world2.shutdown()

    print("Stage 5 — report plumbing:")
    text = report_mod.generate(summary, summary, metric="sample")
    check("report generated with matching-suite comparison",
          "+0.0 points" in text and "NOT comparable" not in text)

    print()
    failed = RESULTS.count(False)
    if failed:
        print("FIRST-MILE TEST FAILED: %d of %d checks."
              % (failed, len(RESULTS)))
        sys.exit(1)
    print("FIRST-MILE TEST PASSED: all %d checks." % len(RESULTS))


if __name__ == "__main__":
    main()
