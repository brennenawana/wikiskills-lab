#!/usr/bin/env python3
"""Engine selftests — prove the budget meter, gateway, look ledger, and
suite runner behave correctly ON THIS MACHINE before any real spend.

  python3 engine/selftest.py

Same doctrine as the recorder probes: trust the probe, not the brochure.
No credentials, no network, no spend — a fake upstream stands in for every
real API. Exit 0 = ready.
"""

import http.server
import json
import os
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "gateway"))
sys.path.insert(0, os.path.join(HERE, "budget"))
sys.path.insert(0, os.path.join(HERE, "measure"))

from meter import Meter, BudgetStop, LookLedger      # noqa: E402
from gateway import Gateway, parse_cli_result        # noqa: E402
import runner as runner_mod                          # noqa: E402

RESULTS = []


def check(name, ok, note=""):
    RESULTS.append(bool(ok))
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                           ("  -- " + note) if (note and not ok) else ""))


def tmpdir():
    return tempfile.mkdtemp(prefix="wsl-selftest-")


# --------------------------------------------------------------- meter

def test_meter():
    print("Budget meter:")
    d = tmpdir()
    caps = {"unit": "usd", "caps": [
        {"scope": "total", "limit": 1.0, "consequence": "full stop"},
        {"scope": "run:base", "limit": 0.5, "consequence": "halt run"}]}
    m = Meter(os.path.join(d, "spend.jsonl"), caps)

    m.precheck(0.4, tags={"run": "base"})
    m.record(0.4, tags={"run": "base"})
    check("spend within caps allowed and recorded",
          abs(m.spent("total") - 0.4) < 1e-9)

    stopped = False
    try:
        m.precheck(0.2, tags={"run": "base"})   # 0.4 + 0.2 > run cap 0.5
    except BudgetStop as exc:
        stopped = exc.scope == "run:base" and "halt run" in exc.consequence
    check("scoped cap stops BEFORE the spend, names its consequence",
          stopped)
    check("the blocked call spent nothing (fail closed)",
          abs(m.spent("total") - 0.4) < 1e-9)

    m.record(0.5, tags={"run": "other"})
    stopped = False
    try:
        m.precheck(0.2, tags={"run": "other"})  # 0.9 + 0.2 > total 1.0
    except BudgetStop as exc:
        stopped = exc.scope == "total"
    check("total cap enforced across runs", stopped)

    m2 = Meter(os.path.join(d, "spend.jsonl"), caps)
    check("totals recomputed from the ledger, not from memory",
          abs(m2.spent("total") - 0.9) < 1e-9)


# --------------------------------------------------------------- looks

def test_looks():
    print("Test-look ledger:")
    d = tmpdir()
    looks = LookLedger(os.path.join(d, "looks.jsonl"))
    results = os.path.join(d, "results.jsonl")

    refused = False
    try:
        looks.spend("A-s1", results)
    except RuntimeError:
        refused = True
    check("unplanned look refused", refused)

    looks.plan("A-s1")
    looks.spend("A-s1", results)          # run starts; no results yet
    try:
        looks.spend("A-s1", results)      # interrupted, still no results
        cont = True
    except RuntimeError:
        cont = False
    check("interrupted look (no results seen) may continue as same look",
          cont)

    open(results, "w").write('{"id": 1}\n')
    refused = False
    try:
        looks.spend("A-s1", results)
    except RuntimeError:
        refused = True
    check("second look after results exist is refused", refused)


# -------------------------------------------------------------- gateway

class FakeOpenAI(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    fail_next = [True]  # first call returns 500, to prove transport retry

    def log_message(self, *a):
        pass

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if FakeOpenAI.fail_next and FakeOpenAI.fail_next.pop():
            body = b'{"error": "boom"}'
            self.send_response(500)
        else:
            body = json.dumps(
                {"model": "test-model",
                 "choices": [{"message": {"content": "hello"}}],
                 "usage": {"prompt_tokens": 100,
                           "completion_tokens": 50}}).encode()
            self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def test_gateway():
    print("Gateway:")
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeOpenAI)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]

    gw = Gateway(prices={"test-model": {"in": 1.0, "out": 5.0}})
    res = gw.call({"kind": "openai",
                   "base_url": "http://127.0.0.1:%d" % port,
                   "model": "test-model"}, "hi")
    check("openai-style call parsed (after one transport retry)",
          res["text"] == "hello" and res["tokens_in"] == 100
          and res["tokens_out"] == 50)
    expect_usd = 100 * 1.0 / 1e6 + 50 * 5.0 / 1e6
    check("usd computed from pinned prices",
          abs(res["usd"] - expect_usd) < 1e-12)
    server.shutdown()

    # CLI parsing: TWO usage entries must BOTH count, and the highest of
    # the independent accountings wins.
    cli_json = json.dumps({
        "result": "done",
        "total_cost_usd": 0.01,               # CLI's own figure (too low)
        "modelUsage": {
            "claude-haiku-4-5": {"inputTokens": 1000, "outputTokens": 200,
                                 "costUSD": 0.002},
            "claude-opus-5": {"inputTokens": 4000, "outputTokens": 800,
                              "costUSD": 0.04}}})
    parsed = parse_cli_result(cli_json)
    check("CLI usage: ALL model entries summed",
          parsed["tokens_in"] == 5000 and parsed["tokens_out"] == 1000)
    check("CLI cost: highest of independent accountings billed",
          abs(parsed["usd"] - 0.042) < 1e-9,
          "got %s" % parsed["usd"])


# --------------------------------------------------------------- runner

def test_runner():
    print("Suite runner:")
    d = tmpdir()
    suite = {"v": 1, "name": "selftest", "version": "1",
             "tasks": [
                 {"id": "t1", "instruction": "say ok",
                  "scorer": {"kind": "exact", "expected": "canned-answer"}},
                 {"id": "t2", "instruction": "say ok",
                  "scorer": {"kind": "contains", "expected": "missing"}},
                 {"id": "t3", "instruction": "say ok",
                  "scorer": {"kind": "token-budget", "max_tokens": 10}}]}
    caps = {"unit": "usd", "caps": [
        {"scope": "total", "limit": 5.0, "consequence": "stop"}]}
    meter = Meter(os.path.join(d, "spend.jsonl"), caps)
    cfg = {"kind": "canned", "text": "canned-answer"}

    s1 = runner_mod.run_suite(suite, cfg, meter, "base", d, 0.0)
    check("scores computed per task (1 pass, 1 fail, 1 process-pass)",
          s1["n_tasks"] == 3 and abs(s1["mean_score"] - 2 / 3) < 1e-9,
          json.dumps(s1["per_task"]))

    results = os.path.join(d, "base", "results.jsonl")
    rows_before = open(results).read()
    s2 = runner_mod.run_suite(suite, cfg, meter, "base", d, 0.0)
    check("re-run resumes from checkpoint (no task repeated)",
          open(results).read() == rows_before and s2["n_tasks"] == 3)

    tight = Meter(os.path.join(d, "spend2.jsonl"),
                  {"unit": "usd", "caps": [
                      {"scope": "total", "limit": 0.001,
                       "consequence": "stop"}]})
    stopped = False
    try:
        runner_mod.run_suite(suite, cfg, tight, "blocked", d, 0.01)
    except BudgetStop:
        stopped = True
    check("runner prechecks the meter before every task", stopped)
    check("blocked run wrote no result rows",
          not os.path.exists(os.path.join(d, "blocked", "results.jsonl")))


def main():
    for fn in (test_meter, test_looks, test_gateway, test_runner):
        fn()
        print()
    failed = RESULTS.count(False)
    if failed:
        print("RESULT: %d of %d selftests FAILED. Do not run real "
              "measurements." % (failed, len(RESULTS)))
        sys.exit(1)
    print("RESULT: all %d selftests passed." % len(RESULTS))


if __name__ == "__main__":
    main()
