# WikiSkills Lab

A coach for your AI development setup.

You point it at your project. It watches how you and your coding agent really
work, measures what is happening, helps you pick one thing to improve, and then
improves it with evidence — not with opinions. At the end you get a before/after
number that you helped define, plus the improvements installed into your daily
work.

It runs as an agent session inside your own tools. There is nothing to deploy
and no account to create.

## How it works

Five steps, in order. You steer as much as you want; at every question you get a
recommendation you can accept or override.

1. **Interview.** The coach asks about your project, your tools, and how you
   work. About 15 minutes.
2. **Observe.** You do one or more real tasks the normal way. The coach records
   what actually happened: what was read, what was called, what it cost.
3. **Diagnose.** The records become findings. You pick the one thing to improve
   — or ask for a ranked list with reasons.
4. **Measure.** Together you build a small, honest test from your own real work,
   and measure today's score. Budgets and stop rules are generated for you and
   shown for approval.
5. **Improve.** An evolution loop proposes changes (skills, instruction files,
   settings — anything text-shaped), keeps only what provably helps, and rolls
   back what does not.

## Does this actually work?

We ran the full loop on a public spreadsheet benchmark before writing this
repository. Evolved skills raised a cheap model's score on 100 held-out tasks
from **36% to 76%**, p < 0.001, while cutting inference cost per solved task
about 3×. The complete record — the frozen rules, every dollar, the winning
skill, the raw results — is in [`benchmarks/spreadsheet/`](benchmarks/spreadsheet/).
Read it before you trust us.

## Quick start

1. Clone this repository **next to** your project (not inside it):

   ```
   cd ~/code        # or wherever your project lives
   git clone https://github.com/brennenawana/wikiskills-lab.git
   ```

2. Open your coding agent in the `wikiskills-lab` folder.

3. Say: **"Read START.md and follow it."**

   (If your agent is Claude Code, Cursor, or a tool that reads `AGENTS.md`, it
   finds START.md by itself — just say hello.)

That is the whole setup. The interview begins, and everything after that is
explained as it happens.

## Your data stays yours

Everything generated for you — answers, recordings, test tasks, results — lives
in the `workspace/` folder, which git ignores. It never leaves your machine and
is never committed. Delete `workspace/` and every trace is gone.

## Status

This is an early version. What works today:

| Part | Status |
|---|---|
| Step 1 — Interview | Ready |
| Step 2 — Observe (recorder, checklist, probes) | Ready |
| Steps 3–5 — Diagnose, Measure, Improve | Being built, in that order |
| Spreadsheet case study | Complete — full record with receipts |

## Credits

The evolution loop and its role prompts come from **WikiSkill** (Tang et al.,
Google Research, arXiv:2608.27454). Full credits and lineage: [`CREDITS.md`](CREDITS.md).
