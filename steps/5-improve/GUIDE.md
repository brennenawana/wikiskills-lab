# Step 5 — Improve

**Goal:** run the evolution loop against the step-4 measuring stick, keep
only what provably helps, and end with a before/after number plus artifacts
installed into daily work.

Preconditions, all hard: an approved, frozen contract
(`workspace/engagements/<current>/contract/`), a baseline (`workspace/engagements/<current>/runs/baseline/`), and green
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
- **Seeds:** the outcome of one evolution run depends partly on luck. If
  the contract chose the local tier, it prescribed more seeds for exactly
  that reason.

## Stage 2 — Run

The loop lives in `engine/evolve/loop.py`; the benchmark adapter shows the
complete wiring (gateway + meter + rollout + roles) in ~30 lines. Every
step checkpoints `state.json`; a budget stop or interruption resumes with
the same command. Append a journal row when the run starts and when it ends
(`--event session`), and one for every gate outcome worth finding again —
an accepted skill, a budget stop, a plateau (`--event decision`). Watch machine load before parallel seeds: count TOTAL
concurrent agent processes, and stay near 12–15 on a shared 16 GB machine.

While it runs, the user does nothing. The wiki's `skill-impact.md` is the
audit trail — written by the harness only, never by a model — and is the
first thing to read when curious about what happened.

## Stage 3 — The held-out measurement

One look per evolved skill set, planned in the contract, spent in
`workspace/engagements/<current>/runs/looks.jsonl` BEFORE the evaluation starts, exactly as the
engine's look ledger enforces. Nobody — human or agent — reads per-task
results before the comparison is computed. Then generate the report:

```
python3 engine/report/report.py --before workspace/engagements/<current>/runs/baseline/summary.json \
    --after workspace/engagements/<current>/runs/after/summary.json --out workspace/engagements/<current>/runs/REPORT.md
```

The report states the change, the noise floor for the suite's size, and
which tasks moved. Read it against the contract's §7 thresholds — the
verdict was defined before the data, so this part is mechanical.

## Stage 4 — Adopt, or roll back

**The user's skill files are theirs.** Three rules govern adoption:

1. Installing an artifact into their world (their skills directory,
   instruction file, or pipeline config — the harness note in `harness/`
   says where) is always an **explicit, approved step**. Never a silent
   write.
2. Every installed artifact carries a **provenance header**: which
   engagement produced it, which suite version, what it scored. A record
   copy stays in `workspace/skills/`.
3. Hand edits afterwards are always allowed — it is their file — but a
   hand edit **expires the before/after claim**. To get the number back,
   the edit goes through the gate as a proposal (see below).

Then:

- **Threshold met:** install as above; keep the wiki and run records —
  they are the provenance. Offer to install or refresh the coach skill
  (`harness/skill/README.md`) so the next improvement can start from
  inside their project.
- **Not met:** the artifacts stay out, the baseline stands, and the record
  of what was tried is kept — a written record of a failed idea saves the
  next attempt from repeating it. Say this to the user without apology; it
  is the system working.
- Either way: light monitoring. Re-run the suite occasionally; when the
  suite goes stale (the work has changed), redraw it from fresh observed
  tasks under a new suite version and a new baseline.

## Your own ideas (user proposals)

The gate does not care who wrote a proposal. Two ways in:

- **A direct proposal.** The user's idea, formatted as the same
  create/patch object the proposer uses (format:
  `prompts/skill-proposer.txt`), submitted with
  `engine/evolve/loop.py::apply_user_proposal` — the benchmark adapter
  shows the wiring (`run.py propose`). It is evaluated on the validation
  tasks, accepted only on strict improvement, and recorded in
  `skill-impact.md` with `author: user`. Same rules, same budgets, one
  difference: a **rejected** user proposal does not advance the loop's
  plateau counter (a human experiment is not a proposer failure); an
  accepted one resets it.
- **A hint.** Write the idea into the run's `wiki/owner-notes.md`
  ("I think the real cause is X — look at trace Y"). Both optimizer roles
  see it in their context, labeled as coming from the human owner. It
  steers the next iteration without bypassing anything.

## Revisiting and improving existing skills

For a workflow that shifted, an adopted artifact worth re-checking, or a
skill file the user wrote themselves and wants improved. It is the same
machinery — **the existing skill is the base** — plus two specifics:

1. Open a new engagement (step 3, focus = this skill's job), and build the
   suite from **current** work under a new suite version: the old suite
   measured the old workflow.
2. Run the baseline **twice — with and without the skill**. One extra
   suite run, and it answers the question everything depends on: what is
   this skill contributing today? If the answer is nothing (or harm), the
   honest options are rewrite or retirement, and the user should choose
   knowing that number.

Then: copy the skill into the new run's `skills/` layer before starting
the loop — the loop's baseline is measured with it active, the proposer
patches it through the gate (in packet mode it receives the full current
skill text, so patch targets can match exactly), and adoption writes the
improved version back to their real file with approval, per the rules
above.

## Files this step owns

- `workspace/engagements/<current>/runs/<run>/` — state.json, wiki/, skills/, raw/ traces,
  spend.jsonl per evolution run
- `workspace/engagements/<current>/runs/looks.jsonl` — the held-out look ledger
- `workspace/engagements/<current>/runs/REPORT.md` — the before/after report
- `workspace/skills/` — adopted artifacts, copied from the winning run
