# Step 5 — Improve

**Goal:** run the evolution loop against the step-4 measuring stick, keep
only what provably helps, and end with a before/after number plus artifacts
installed into daily work.

Preconditions, all hard: an approved, frozen contract
(`workspace/contract/`), a baseline (`workspace/runs/baseline/`), and green
`engine/selftest.py` on this machine. The loop's method comes from the
WikiSkill paper (`prompts/NOTICE.md`); the full real example of this step is
`benchmarks/spreadsheet/`.

## How the loop works (what to tell the user, in five sentences)

An optimizer model studies the traces of real attempts and keeps notes in a
wiki that is never rolled back. Each round it proposes ONE change — a skill
file, or a patch to one. The change is tried on the validation tasks and
kept only if the score strictly improves; otherwise it is rolled back and
the rejection is recorded so it is not tried again. The loop stops by
itself: at a perfect validation score, after 3 rounds with nothing
accepted, at round K, or at any budget cap. Only then does the held-out
measurement happen — once.

## Stage 1 — Configure

- **Executor** = the user's own setup, unchanged. For agentic file tasks it
  needs a harness the engine can drive (the claude-cli backend today; a
  custom pipeline can implement the rollout function the same way
  `benchmarks/spreadsheet/adapter/` does).
- **Optimizer tier** — the user's call, made with the evidence: cheap
  self-evolution works; a frontier optimizer buys run-to-run reliability at
  extra cost (see the case study's per-seed spread, REPORT.md §5.3). The
  contract already recorded this choice and its budgets.
- **Proposer mode** is automatic: a claude-cli optimizer explores wiki and
  traces itself with the Read tool ("react"); every other backend — local
  models included — gets the wiki and sampled traces delivered in the
  message ("packet"). Both obey the same rules.
- **Seeds:** one evolution run is a lottery ticket. If the contract chose
  the local tier, it prescribed more seeds for exactly that reason.

## Stage 2 — Run

The loop lives in `engine/evolve/loop.py`; the benchmark adapter shows the
complete wiring (gateway + meter + rollout + roles) in ~30 lines. Every
step checkpoints `state.json`; a budget stop or interruption resumes with
the same command. Watch machine load before parallel seeds: count TOTAL
concurrent agent processes, and stay near 12–15 on a shared 16 GB machine.

While it runs, the user does nothing. The wiki's `skill-impact.md` is the
audit trail — written by the harness only, never by a model — and is the
first thing to read when curious about what happened.

## Stage 3 — The held-out measurement

One look per evolved skill set, planned in the contract, spent in
`workspace/runs/looks.jsonl` BEFORE the evaluation starts, exactly as the
engine's look ledger enforces. Nobody — human or agent — reads per-task
results before the comparison is computed. Then generate the report:

```
python3 engine/report/report.py --before workspace/runs/baseline/summary.json \
    --after workspace/runs/after/summary.json --out workspace/runs/REPORT.md
```

The report states the change, the noise floor for the suite's size, and
which tasks moved. Read it against the contract's §7 thresholds — the
verdict was defined before the data, so this part is mechanical.

## Stage 4 — Adopt, or roll back

- **Threshold met:** install the accepted artifacts into daily work (the
  harness note in `harness/` says where they live — instruction files,
  skills directories, pipeline config). Keep the wiki and the run records;
  they are the provenance.
- **Not met:** the artifacts stay out, the baseline stands, and the record
  of what was tried is kept — a documented dead end saves the next attempt
  from repeating it. Say this to the user without apology; it is the
  system working.
- Either way: light monitoring. Re-run the suite occasionally; when the
  suite goes stale (the work has changed), redraw it from fresh observed
  tasks under a new suite version and a new baseline.

## Files this step owns

- `workspace/runs/<run>/` — state.json, wiki/, skills/, raw/ traces,
  spend.jsonl per evolution run
- `workspace/runs/looks.jsonl` — the held-out look ledger
- `workspace/runs/REPORT.md` — the before/after report
- `workspace/skills/` — adopted artifacts, copied from the winning run
