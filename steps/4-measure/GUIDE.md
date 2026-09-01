# Step 4 — Measure

**Goal:** turn the chosen focus into a measuring stick — a metric, a frozen
task suite, mechanical scorers, generated rules the user approves, and
today's baseline score. Nothing in step 5 may run before all of that
exists.

Input: `workspace/engagements/<current>/focus.md`. Tools: `engine/measure/runner.py`
(the suite runner), `engine/budget/meter.py` (enforced by the runner),
`engine/selftest.py` (run it once first — same rule as the recorder
probes: nothing is trusted until proven on this machine).

`<current>` throughout means the active engagement folder named in
`workspace/profile/state.json`.

## Stage 1 — Define the metric with the user

One sentence, one direction, one unit. ("Percent of suite tasks solved on
the first attempt, higher is better." "Tokens ingested per ticket, lower
is better.") Write it at the top of the suite file. If the metric cannot
be scored mechanically, go back — `scoring.md` axis M was supposed to
catch this.

## Stage 2 — Build the task suite

Draw tasks from the user's real work: the observed session's captures, and
more like it. Format: `suite-format.md`. Guidance:

- **5–20 tasks** to start. Fewer measures nothing; more delays the loop.
- Each task must be **repeatable**: same input, same expected behavior,
  next month. Inputs that live in moving systems get frozen copies
  (recorded captures now; full capsule replay machinery arrives in a later
  version — until then prefer tasks whose inputs are files you can snapshot
  into the suite directory).
- **Split rule:** if the suite will drive the step-5 improvement loop,
  reserve a held-out part (about a third) that the loop never sees, and
  plan looks at it in the contract. If the suite only measures a
  before/after process change, one set is fine — but frozen either way.
- Version the suite (`"version": "1"`). Any change to any task afterwards
  is version 2, and numbers are only comparable within a version.

## Stage 3 — Choose scorers (deterministic first)

In order of preference:

1. `command` — the user's own checker: tests pass, a diff comparator, a
   ledger threshold script. Exit 0 is a pass. This is the best scorer
   because it encodes their definition of done.
2. `exact` / `contains` — for tasks with a known answer.
3. `token-budget` — for process metrics, straight from usage.
4. A model-as-judge scorer is a last resort and is **not supported yet**;
   if nothing mechanical exists, narrow the task until something does.

## Stage 4 — Dry run (free, mandatory)

```
python3 engine/measure/runner.py --suite workspace/engagements/<current>/suite/suite.json \
    --models workspace/profile/models.json --role executor \
    --caps workspace/engagements/<current>/contract/caps.json --run-name dryrun \
    --out workspace/engagements/<current>/runs --dry-run
```

The canned backend answers every task for free; what this proves is the
suite file, every scorer, and the checkpointing — before any token is
spent. A scorer that errors here would have wasted the baseline.

## Stage 5 — Generate the rules, get approval, freeze

Fill `contract-template.md` into `workspace/engagements/<current>/contract/CONTRACT.md`:
budgets in the user's own cost unit (dollars, tokens, GPU-minutes — from
the interview's cost reality), a measured-not-guessed projection per task
(from the dry run's shape and one or two priced calls if needed), stop
rules with named consequences, and the look plan for any held-out part.
Walk the user through it in plain words — **approved, not assigned as
reading**. Then freeze: write `caps.json`, and record SHA-256 hashes of
`suite.json` and `caps.json` in `workspace/engagements/<current>/contract/binding.json`. After
the freeze, changes are amendments at the bottom of the contract, never
silent edits.

## Stage 6 — Run the baseline

```
python3 engine/measure/runner.py --suite workspace/engagements/<current>/suite/suite.json \
    --models workspace/profile/models.json --role executor \
    --caps workspace/engagements/<current>/contract/caps.json --run-name baseline \
    --out workspace/engagements/<current>/runs
```

The runner prechecks the meter before every task, checkpoints every
result, and writes `workspace/engagements/<current>/runs/baseline/summary.json`. If it stops on
a cap: that is the system working — re-project from the measured rows,
amend the contract with the user, resume the same command.

**Headroom check before celebrating or despairing:**

- Baseline near 100% → the suite is too easy for the current setup; the
  metric has no room to show improvement. Rescope (harder or different
  tasks) under a new suite version.
- Baseline at 0% → suspect the scorers before the model. Re-check with the
  dry run; if the scorers are right and the tasks are truly impossible,
  rescope.
- Anything with real room in both directions is a good baseline. Tell the
  user the number plainly, with cost: "Today: 40% at 90K tokens per run."

## Close out

Update `state.json` (`"step": "4-measure", "stage": "done"`) and record the
baseline in the journal — the number and its cost, so a session weeks later
can quote it without re-reading the run:

```
python3 engine/journal.py append --event artifact --step 4-measure \
  --engagement <nnn-slug> \
  --note "Baseline: <score> at <cost> per run; suite v<n>, contract frozen."
```

Files this
step owns: `workspace/engagements/<current>/suite/suite.json`, `workspace/engagements/<current>/contract/
{CONTRACT.md, caps.json, binding.json}`, `workspace/engagements/<current>/runs/baseline/`.
Tell the user what happens next: step 5, the improvement loop — and if it
is not yet available in this version, say so and stop; the baseline is
frozen and waiting.
