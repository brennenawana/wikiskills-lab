#!/usr/bin/env python3
"""Run the spreadsheet benchmark through the engine.

  python3 run.py verify              # data + checker + manifest sanity
  python3 run.py evolve --run-name C-s1 --optimizer claude-opus-5 \
      [--executor claude-haiku-4-5]
  python3 run.py propose --run-name C-s1 --file my_idea.json
                                     # a human idea, through the same gate
  python3 run.py eval --run-name eval-C-s1 --skills-from C-s1 --split test

Every command is metered (caps.json here; edit before real runs) and
checkpointed. `eval` spends a test look in looks.jsonl BEFORE running —
one look per skills source, exactly as the case-study contract did.

Real runs need the Claude Code CLI on a logged-in subscription (or edit
models.json for API/local backends), openpyxl+pandas for the checker, and
real money/quota — read ../CONTRACT.md and ../REPORT.md first.
"""

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
for sub in ("gateway", "budget", "evolve", "measure"):
    sys.path.insert(0, str(REPO / "engine" / sub))

import sbench                                        # noqa: E402
from gateway import Gateway                          # noqa: E402
from meter import Meter, LookLedger                  # noqa: E402
import loop as loop_mod                              # noqa: E402

RUNS = HERE.parent / "runs_local"        # git-ignored with data/
PRICES = {"claude-haiku-4-5": {"in": 1.00, "out": 5.00},
          "claude-opus-5": {"in": 5.00, "out": 25.00}}
DEFAULT_CAPS = {"unit": "usd", "caps": [
    {"scope": "total", "limit": 25.0,
     "consequence": "full stop; edit caps.json deliberately to raise"},
]}
TASK_DESC = "spreadsheet manipulation tasks (SpreadsheetBench)"


def get_meter(run_name):
    caps_path = HERE / "caps.json"
    if not caps_path.exists():
        caps_path.write_text(json.dumps(DEFAULT_CAPS, indent=1))
        print("wrote default caps to %s — review before real runs"
              % caps_path)
    caps = json.loads(caps_path.read_text())
    return Meter(str(RUNS / run_name / "spend.jsonl"), caps)


def cmd_verify(args):
    manifest = sbench.load_manifest()
    print("manifest: %d/%d/%d tasks, seed %s"
          % (len(manifest["splits"]["train"]),
             len(manifest["splits"]["val"]),
             len(manifest["splits"]["test"]), manifest["seed"]))
    dataset = sbench.load_dataset()
    print("dataset: %d tasks on disk" % len(dataset))
    sample = sbench.tasks_by_id(manifest["splits"]["val"][:3])
    ok_all = True
    for t in sample:
        ok, why = sbench.checker_selftest(t)
        print("  task %-8s checker selftest: %s %s"
              % (t["id"], "PASS" if ok else "FAIL", why))
        ok_all &= ok
    print("VERIFY %s" % ("OK" if ok_all else "FAILED"))
    sys.exit(0 if ok_all else 1)


def cmd_evolve(args):
    manifest = sbench.load_manifest()
    train = sbench.tasks_by_id(manifest["splits"]["train"])
    val = sbench.tasks_by_id(manifest["splits"]["val"])
    run_dir = RUNS / args.run_name
    meter = get_meter(args.run_name)
    tag = {"run": args.run_name}
    gw = Gateway(prices=PRICES)
    executor_cfg = {"kind": "claude-cli", "model": args.executor}
    optimizer_cfg = {"kind": "claude-cli", "model": args.optimizer}
    rollout = sbench.make_rollout_fn(gw, executor_cfg,
                                     run_dir / "workdirs", meter, tag)
    roles = loop_mod.Roles(gw, optimizer_cfg, TASK_DESC, meter=meter,
                           run_tag=tag)
    state = loop_mod.run_evolution(run_dir, train, val, rollout, roles,
                                   k=8, plateau_stop=3, meter=meter,
                                   iteration_projection=6.0, run_tag=tag)
    print(json.dumps(state, indent=1))


def cmd_propose(args):
    """A user-authored proposal (create/patch JSON) into an existing run,
    through the same strict-improvement gate as the model's proposals."""
    proposal = json.loads(Path(args.file).read_text())
    manifest = sbench.load_manifest()
    val = sbench.tasks_by_id(manifest["splits"]["val"])
    run_dir = RUNS / args.run_name
    meter = get_meter(args.run_name)
    tag = {"run": args.run_name}
    gw = Gateway(prices=PRICES)
    executor_cfg = {"kind": "claude-cli", "model": args.executor}
    rollout = sbench.make_rollout_fn(gw, executor_cfg,
                                     run_dir / "workdirs", meter, tag)
    result = loop_mod.apply_user_proposal(run_dir, proposal, val, rollout)
    print(json.dumps(result, indent=1))


def cmd_eval(args):
    manifest = sbench.load_manifest()
    tasks = sbench.tasks_by_id(manifest["splits"][args.split])
    run_dir = RUNS / args.run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    meter = get_meter(args.run_name)
    tag = {"run": args.run_name}

    looks = LookLedger(str(RUNS / "looks.jsonl"))
    key = "%s:%s" % (args.skills_from or "no-skill", args.split)
    looks.plan(key)
    results_file = run_dir / "results.json"
    looks.spend(key, str(results_file))   # spent BEFORE the run

    gw = Gateway(prices=PRICES)
    executor_cfg = {"kind": "claude-cli", "model": args.executor}
    skill_section = ""
    if args.skills_from:
        sys.path.insert(0, str(REPO / "engine" / "evolve"))
        import wikistore
        skill_section = wikistore.skills_text(
            RUNS / args.skills_from / "skills")

    progress = run_dir / "eval_progress.jsonl"
    done = set()
    if progress.exists():
        for line in progress.read_text().splitlines():
            done.add(json.loads(line)["id"])
    for task in tasks:
        if str(task["id"]) in done:
            continue
        r = sbench.run_task(gw, executor_cfg, task, skill_section,
                            run_dir / "workdirs", meter, tag)
        with progress.open("a") as fh:
            fh.write(json.dumps({k: r[k] for k in ("id", "score",
                                                   "crash")}) + "\n")

    rows = [json.loads(l) for l in progress.read_text().splitlines()]
    out = {"run": args.run_name, "split": args.split, "n": len(rows),
           "mean": sum(r["score"] for r in rows) / max(len(rows), 1),
           "skills_from": args.skills_from,
           "per_task": {r["id"]: r["score"] for r in rows}}
    results_file.write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("run", "split", "n", "mean")},
                     indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("verify")
    e = sub.add_parser("evolve")
    e.add_argument("--run-name", required=True)
    e.add_argument("--optimizer", required=True)
    e.add_argument("--executor", default="claude-haiku-4-5")
    p = sub.add_parser("propose")
    p.add_argument("--run-name", required=True)
    p.add_argument("--file", required=True,
                   help="JSON file with the create/patch proposal")
    p.add_argument("--executor", default="claude-haiku-4-5")
    v = sub.add_parser("eval")
    v.add_argument("--run-name", required=True)
    v.add_argument("--skills-from", default=None)
    v.add_argument("--split", default="test",
                   choices=["train", "val", "test"])
    v.add_argument("--executor", default="claude-haiku-4-5")
    args = ap.parse_args()
    os.makedirs(RUNS, exist_ok=True)
    {"verify": cmd_verify, "evolve": cmd_evolve, "propose": cmd_propose,
     "eval": cmd_eval}[args.cmd](args)


if __name__ == "__main__":
    main()
