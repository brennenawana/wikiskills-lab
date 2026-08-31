#!/usr/bin/env python3
"""Suite runner — measures a task suite against one model configuration.

Used for the baseline in step 4 and for every later measurement. Three
habits are built in and not optional:

- the budget meter is prechecked before EVERY task (fail closed),
- results are checkpointed per task, so an interruption loses nothing,
- the summary is recomputed from the results file, never from memory.

Usage:
  python3 runner.py --suite workspace/suite/suite.json \
      --models workspace/profile/models.json --role executor \
      --caps workspace/contract/caps.json \
      --run-name baseline --out workspace/runs

Dry run first, always (free, proves the scorers work):
  python3 runner.py ... --dry-run
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "gateway"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "budget"))
from gateway import Gateway, GatewayError          # noqa: E402
from meter import Meter, BudgetStop                # noqa: E402


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(
        timespec="milliseconds")


# ------------------------------------------------------------------ scorers

def score(task, result):
    """Return (score 0..1, note). Deterministic scorers only; if a task
    needs judgment, it should not be in the suite yet (see the step-4
    guide about scorer choices)."""
    scorer = task.get("scorer") or {}
    kind = scorer.get("kind")
    text = (result.get("text") or "").strip()

    if kind == "exact":
        return (1.0 if text == str(scorer["expected"]).strip() else 0.0), None
    if kind == "contains":
        return (1.0 if str(scorer["expected"]) in text else 0.0), None
    if kind == "token-budget":
        used = (result.get("tokens_in") or 0) + (result.get("tokens_out") or 0)
        limit = int(scorer["max_tokens"])
        return (1.0 if used <= limit else 0.0), "used=%d limit=%d" % (used,
                                                                      limit)
    if kind == "command":
        # The user's own checker: gets the response in a file, exits 0 on
        # pass. This is the door to real scorers (tests, diff checkers).
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                         encoding="utf-8") as fh:
            fh.write(text)
            out_path = fh.name
        env = dict(os.environ, TASK_OUTPUT=out_path,
                   TASK_ID=str(task.get("id")))
        try:
            proc = subprocess.run(scorer["command"], shell=True, env=env,
                                  capture_output=True,
                                  timeout=scorer.get("timeout_s", 120))
            return (1.0 if proc.returncode == 0 else 0.0), None
        finally:
            os.unlink(out_path)
    raise ValueError("unknown scorer kind: %r (task %s)"
                     % (kind, task.get("id")))


# ------------------------------------------------------------------- runner

def run_suite(suite, model_cfg, meter, run_name, out_dir, projected_cost,
              gateway=None):
    gateway = gateway or Gateway(prices=suite.get("prices"))
    run_dir = os.path.join(out_dir, run_name)
    os.makedirs(run_dir, exist_ok=True)
    results_path = os.path.join(run_dir, "results.jsonl")

    done = set()
    if os.path.exists(results_path):
        with open(results_path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    done.add(str(json.loads(line)["id"]))

    tasks = suite["tasks"]
    for task in tasks:
        tid = str(task["id"])
        if tid in done:
            continue
        meter.precheck(projected_cost, tags={"run": run_name})
        try:
            result = gateway.call(
                model_cfg, task["instruction"],
                system=suite.get("system"),
                max_tokens=suite.get("max_tokens", 4096))
        except GatewayError as exc:
            row = {"id": tid, "ts": _now(), "score": 0.0,
                   "error": str(exc)[:300], "cost": 0.0}
        else:
            value, note = score(task, result)
            cost = result["usd"] if meter.unit == "usd" else \
                (result["tokens_in"] + result["tokens_out"])
            meter.record(cost, tags={"run": run_name, "task": tid},
                         model=result.get("model"))
            row = {"id": tid, "ts": _now(), "score": value,
                   "tokens_in": result["tokens_in"],
                   "tokens_out": result["tokens_out"],
                   "cost": cost}
            if note:
                row["note"] = note
        with open(results_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    return summarize(results_path, run_dir, suite, run_name)


def summarize(results_path, run_dir, suite, run_name):
    rows = []
    with open(results_path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    n = len(rows)
    summary = {
        "v": 1, "ts": _now(), "run": run_name,
        "suite": suite.get("name"), "suite_version": suite.get("version"),
        "n_tasks": n,
        "mean_score": (sum(r["score"] for r in rows) / n) if n else None,
        "total_cost": sum(r.get("cost", 0.0) for r in rows),
        "errors": sum(1 for r in rows if r.get("error")),
        "per_task": {r["id"]: r["score"] for r in rows},
    }
    path = os.path.join(run_dir, "summary.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1)
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--suite", required=True)
    ap.add_argument("--models", required=True,
                    help="JSON file with model configs by role")
    ap.add_argument("--role", default="executor")
    ap.add_argument("--caps", required=True,
                    help="caps JSON (from the approved contract)")
    ap.add_argument("--run-name", required=True)
    ap.add_argument("--out", default="workspace/runs")
    ap.add_argument("--projected-task-cost", type=float, default=None,
                    help="expected cost per task, used by the precheck; "
                         "defaults to the caps file's projection")
    ap.add_argument("--dry-run", action="store_true",
                    help="run with the free canned backend to prove the "
                         "suite file and scorers work before spending")
    args = ap.parse_args()

    suite = json.load(open(args.suite, encoding="utf-8"))
    caps = json.load(open(args.caps, encoding="utf-8"))
    models = json.load(open(args.models, encoding="utf-8"))
    model_cfg = {"kind": "canned", "text": "dry-run"} if args.dry_run \
        else models[args.role]
    projected = args.projected_task_cost
    if projected is None:
        projected = caps.get("projected_task_cost", 0.0)

    meter = Meter(os.path.join(args.out, args.run_name, "spend.jsonl"), caps)
    try:
        summary = run_suite(suite, model_cfg, meter, args.run_name, args.out,
                            projected)
    except BudgetStop as exc:
        print("STOPPED-BUDGET: %s" % exc, file=sys.stderr)
        print("Completed tasks are checkpointed; the same command resumes "
              "after the owner raises the cap (contract amendment).",
              file=sys.stderr)
        sys.exit(3)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
