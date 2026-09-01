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
import subprocess
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "gateway"))
sys.path.insert(0, os.path.join(HERE, "budget"))
sys.path.insert(0, os.path.join(HERE, "measure"))
sys.path.insert(0, os.path.join(HERE, "evolve"))
sys.path.insert(0, os.path.join(HERE, "capsule"))
sys.path.insert(0, os.path.join(HERE, "report"))
sys.path.insert(0, HERE)

from meter import Meter, BudgetStop, LookLedger      # noqa: E402
from gateway import Gateway, parse_cli_result, extract_json  # noqa: E402
import runner as runner_mod                          # noqa: E402
import wikistore                                     # noqa: E402
import loop as loop_mod                              # noqa: E402
import capsule as capsule_mod                        # noqa: E402
import report as report_mod                          # noqa: E402
import journal as journal_mod                        # noqa: E402

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


# ------------------------------------------------------------ evolve loop

class FakeRoles:
    """Scripted maintainer + proposer: iteration 1 creates a skill that
    will pass the gate, iteration 2 patches it and fails, then no_action
    until the plateau stop fires."""

    def maintain(self, run_dir, results, iteration, trace_dir):
        return wikistore.apply_maintainer_ops(run_dir, {
            "update_index": "# Pattern Index\n\n- [p1](wiki/patterns/p1.md):"
                            " problem + cause + fix.\n",
            "append_log": "iteration %d analyzed" % iteration,
            "create_patterns": [{"name": "p1.md",
                                 "content": "# p1\nEvidence."}],
        }, iteration)

    def propose(self, run_dir, results, iteration, trace_dir):
        if iteration == 1:
            return {"action": "create", "name": "good_skill",
                    "skill_md": "---\nname: good_skill\n---\nDo it right.",
                    "purpose_md": "# PURPOSE\nFrom iteration 1."}
        if iteration == 2:
            return {"action": "patch", "name": "good_skill",
                    "edits": [{"op": "append", "content": "BAD ADVICE"}]}
        return {"action": "no_action"}


def test_evolve():
    print("Evolution loop:")
    d = tmpdir()
    run_dir = os.path.join(d, "run1")

    # Scripted scores: baseline .4; with the created skill .6 (accept);
    # with the bad patch .2 (reject).
    def rollout_fn(tasks, skill_section, iteration, trace_dir):
        if "BAD ADVICE" in skill_section:
            score = 0.2
        elif "good_skill" in skill_section:
            score = 0.6
        else:
            score = 0.4
        results = [{"id": t["id"], "score": score, "crash": False}
                   for t in tasks]
        if trace_dir:
            for r in results:
                with open(os.path.join(str(trace_dir),
                                       "%s.txt" % r["id"]), "w") as fh:
                    fh.write("trace for %s score %.1f" % (r["id"], score))
        return results

    tasks = [{"id": "a"}, {"id": "b"}]
    state = loop_mod.run_evolution(run_dir, tasks, tasks, rollout_fn,
                                   FakeRoles(), k=8, plateau_stop=3)

    check("baseline measured with empty skills",
          any(a["iteration"] == 1 for a in state["accepted"]))
    skills = os.path.join(run_dir, "skills", "good_skill", "SKILL.md")
    good = open(skills).read() if os.path.exists(skills) else ""
    check("gate: improving skill accepted and promoted",
          "Do it right." in good)
    check("gate: worsening patch rejected, skills untouched",
          "BAD ADVICE" not in good)
    check("plateau stop after 3 straight non-accepts",
          state["stop_reason"] == "EARLY-PLATEAU")
    impact = open(os.path.join(run_dir, "wiki",
                               "skill-impact.md")).read()
    check("skill-impact audit trail written by the harness",
          "ACCEPTED" in impact and "REJECTED" in impact
          and "NO_ACTION" in impact)
    check("wiki persisted (patterns + index + log)",
          os.path.exists(os.path.join(run_dir, "wiki", "patterns",
                                      "p1.md")))

    # Interrupted-run resume: state.json carries the loop forward.
    state2 = loop_mod.run_evolution(run_dir, tasks, tasks, rollout_fn,
                                    FakeRoles(), k=8, plateau_stop=3)
    check("finished run resumes as a no-op (checkpointed state)",
          state2["stop_reason"] == "EARLY-PLATEAU"
          and state2["accepted"] == state["accepted"])

    check("extract_json finds the object inside prose",
          extract_json("Here you go:\n{\"action\": \"no_action\"}\nDone.")
          == {"action": "no_action"})

    # --- user proposals: same gate, author recorded, plateau rules ---
    plateau_before = json.load(open(os.path.join(run_dir,
                                                 "state.json")))["plateau"]
    good = loop_mod.apply_user_proposal(
        run_dir, {"action": "patch", "name": "good_skill",
                  "edits": [{"op": "append", "content": "USER IDEA"}]},
        tasks, lambda t, s, i, td: [
            {"id": x["id"], "score": 0.8 if "USER IDEA" in s
             else (0.2 if "BAD ADVICE" in s else 0.6), "crash": False}
            for x in t])
    skills_md = open(os.path.join(run_dir, "skills", "good_skill",
                                  "SKILL.md")).read()
    check("user proposal through the same gate: accepted and promoted",
          good["outcome"] == "accepted" and "USER IDEA" in skills_md)
    state_now = json.load(open(os.path.join(run_dir, "state.json")))
    check("accepted user proposal resets the plateau",
          plateau_before >= 3 and state_now["plateau"] == 0
          and state_now["accepted"][-1]["author"] == "user")
    bad = loop_mod.apply_user_proposal(
        run_dir, {"action": "patch", "name": "good_skill",
                  "edits": [{"op": "append", "content": "BAD ADVICE"}]},
        tasks, lambda t, s, i, td: [
            {"id": x["id"], "score": 0.2 if "BAD ADVICE" in s else 0.8,
             "crash": False} for x in t])
    check("bad user proposal rejected; skills untouched; plateau unmoved",
          bad["outcome"] == "rejected"
          and "BAD ADVICE" not in open(os.path.join(
              run_dir, "skills", "good_skill", "SKILL.md")).read()
          and json.load(open(os.path.join(run_dir,
                                          "state.json")))["plateau"] == 0)
    impact = open(os.path.join(run_dir, "wiki", "skill-impact.md")).read()
    check("impact history names the human author",
          "(author: user)" in impact)

    # --- owner notes + packet-mode context ---
    with open(os.path.join(run_dir, "wiki", "owner-notes.md"), "w") as fh:
        fh.write("Look at the retry helper first.")
    ctx = wikistore.wiki_context(run_dir)
    check("owner notes reach the optimizer context, labeled human",
          "Look at the retry helper first." in ctx
          and "written by the human owner" in ctx)
    trace_dir = os.path.join(run_dir, "raw", "iter_1")
    packet = loop_mod._packet_proposer_context(
        run_dir, [{"id": "a", "score": 0.0, "crash": False}], trace_dir, 1)
    check("packet-mode proposer sees full current skill text",
          "USER IDEA" in packet and "Current skill files" in packet)


# ---------------------------------------------------------------- capsule

def test_capsule():
    print("Capsules:")
    d = tmpdir()
    repo = os.path.join(d, "repo")
    os.makedirs(repo)
    subprocess.run(["git", "init", "-q", repo], check=True)
    open(os.path.join(repo, "f.txt"), "w").write("hello")
    subprocess.run(["git", "-C", repo, "add", "-A"], check=True,
                   capture_output=True)
    subprocess.run(["git", "-C", repo, "-c", "user.email=t@t",
                    "-c", "user.name=t", "commit", "-qm", "x"],
                   check=True, capture_output=True)

    fx = os.path.join(d, "capture")
    os.makedirs(fx)
    open(os.path.join(fx, "0001_GET_x.json"), "w").write(
        '{"request": {"method": "GET", "path": "/x"}, '
        '"response": {"status": 200, "body": {"encoding": "text", '
        '"data": "{}"}}}')

    cap = os.path.join(d, "capsule")
    manifest = capsule_mod.create(cap, "test task", [repo],
                                  fixtures_dir=fx)
    check("capsule pins the repo commit",
          len(manifest["repos"]) == 1
          and len(manifest["repos"][0]["commit"]) == 40)
    ok, _ = capsule_mod.verify(cap)
    check("fresh capsule verifies", ok)
    with open(os.path.join(cap, "fixtures", "0001_GET_x.json"), "a") as fh:
        fh.write(" ")
    ok2, problems = capsule_mod.verify(cap)
    check("tampered fixture is detected", not ok2
          and any("mismatch" in p for p in problems))
    co = capsule_mod.checkout(cap, os.path.join(d, "co"))
    check("disposable checkout materializes the pinned commit",
          os.path.exists(os.path.join(co[0], "f.txt")))


# ----------------------------------------------------------------- report

def test_report():
    print("Report generator:")
    before = {"run": "baseline", "suite": "s", "suite_version": "1",
              "n_tasks": 4, "mean_score": 0.25, "total_cost": 2.0,
              "errors": 0, "per_task": {"a": 0, "b": 0, "c": 0, "d": 1}}
    after = {"run": "after", "suite": "s", "suite_version": "1",
             "n_tasks": 4, "mean_score": 0.75, "total_cost": 1.2,
             "errors": 0, "per_task": {"a": 1, "b": 1, "c": 0, "d": 1}}
    text = report_mod.generate(before, after, metric="tasks solved",
                               artifacts=["good_skill"])
    check("before/after numbers and delta present",
          "25.0%" in text and "75.0%" in text and "+50.0 points" in text)
    check("noise floor stated from suite size", "25.0 points" in text)
    check("improved/regressed tasks listed", "a, b" in text)
    mixed = report_mod.generate(before, dict(after, suite_version="2"))
    check("different suite versions -> NOT comparable warning",
          "NOT comparable" in mixed)


# ---------------------------------------------------------------- journal

def test_journal():
    print("Activity journal:")
    ws = tmpdir()
    path = os.path.join(ws, "journal.jsonl")

    journal_mod.append("First stage done", event="stage",
                       step="1-interview", path=path)
    journal_mod.append("Focus chosen", event="engagement",
                       engagement="001-retries", where="my-project",
                       path=path)
    rows = journal_mod.read(path=path)
    check("rows land in order, nothing lost",
          [r["note"] for r in rows] == ["First stage done", "Focus chosen"])
    check("fields recorded",
          rows[1]["event"] == "engagement"
          and rows[1]["engagement"] == "001-retries"
          and rows[1]["where"] == "my-project"
          and rows[1]["utc"].endswith("Z"))

    # Append-only: the first row is byte-identical after later writes.
    first_line = open(path, encoding="utf-8").readlines()[0]
    journal_mod.append("Third thing", event="artifact", path=path)
    check("earlier rows are never rewritten",
          open(path, encoding="utf-8").readlines()[0] == first_line)

    journal_mod.append("A note\nwith a newline\tand a tab", path=path)
    lines = open(path, encoding="utf-8").readlines()
    check("one row is always one line", len(lines) == 4
          and "newline and a tab" in lines[3])

    journal_mod.append("token is sk-ABCDEFGH12345678 here", path=path)
    text = open(path, encoding="utf-8").read()
    check("secret-shaped text is scrubbed on the way in",
          "sk-ABCDEFGH12345678" not in text and "[SCRUBBED]" in text)

    bad = 0
    for note, event in (("", "session"), ("   ", "session"),
                        ("fine", "not-an-event")):
        try:
            journal_mod.append(note, event=event, path=path)
        except ValueError:
            bad += 1
    check("empty notes and unknown events are refused", bad == 3)

    with open(path, "a", encoding="utf-8") as fh:
        fh.write("this is not json\n")
    tail = journal_mod.tail(2, path=path)
    check("unreadable lines are skipped, not fatal",
          len(tail) == 2 and tail[-1]["note"].startswith("token is"))

    check("tail of an absent journal is empty, not an error",
          journal_mod.tail(5, path=os.path.join(ws, "nope.jsonl")) == [])

    fresh = os.path.join(tmpdir(), "sub", "journal.jsonl")
    journal_mod.append("first ever row", path=fresh)
    check("journal creates its own folder on first write",
          os.path.exists(fresh))


def main():
    for fn in (test_meter, test_looks, test_gateway, test_runner,
               test_evolve, test_capsule, test_report, test_journal):
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
