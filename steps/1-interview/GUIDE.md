# Step 1 — The Interview

**Goal:** learn the user's world well enough to observe it (step 2), and leave
a written profile that any later session can pick up. The question bank is in
`questions.md`; this file says how to run it.

Time promise: tell the user up front this takes about 15 minutes and can stop
and resume at any point. Keep that promise — prefer fewer, better questions.

## How to behave

- One question at a time. Never a form to fill in.
- After each answer, reflect it back in one short sentence so mistakes are
  caught immediately ("So: two repos, one tracker, everything through
  Claude Code — correct?").
- Every question in `questions.md` has a purpose line. If the purpose is
  already satisfied by an earlier answer, skip the question. Do not ask what
  you can safely detect yourself (see stage 3).
- The user can say "you pick" or "skip" at any point. "You pick" means: use
  your recommendation and record that it was a default, not their choice.
- Write answers into the profile files **as they are given** (formats below).
  Update `state.json` when a stage completes.

## The stages

### Stage 0 — Consent (do not skip)

Explain, in plain words and at most five sentences: what the five steps are,
that this stage is questions only, that everything recorded lands in
`workspace/` on this machine and nowhere else, and that deleting that folder
removes everything. Then ask permission to start writing files there. If the
answer is no, stop politely — nothing happens without it.

### Stage 1 — The project map

Find out what "the project" physically is:

- Every repository that belongs to the work, with local paths.
- Every outside service a normal task touches: ticket tracker, CI, cloud
  consoles, package registries, anything the agent reads or writes.
- Which of these the agent touches directly, and which only the human does.

This is the **blast radius** — the full set of things a task can reach. It is
asked first because step 2 must be able to record all of it from the start.
Write it to `profile/blast-radius.md` as two tables (repositories; services).

### Stage 2 — How they work

- Which agent tool (harness) they use, and how they run it.
- Which models, and where those run (local GPU, subscription, API) — and the
  cost reality of each. This later decides budgets and which model does skill
  discovery, so get it concrete: "a local 27B through Ollama" is an answer,
  "some model" is not.
- One typical task, narrated start to finish in their own words: where it
  arrives, what they do, what the agent does, how they judge the result.
- What already bothers them. Record their words; do not translate into your
  own theory yet.

Write to `profile/profile.md` as you go.

### Stage 3 — Harness lock-in

Identify the harness precisely, preferring cheap checks over questions: which
instruction files exist in their project (`CLAUDE.md`, `AGENTS.md`,
`.cursorrules`), which CLIs are on PATH, what stage-2 said. Then open the
matching file in `harness/` (for example `harness/claude-code.md`) and follow
it. Tell the user two honest things from it:

1. What can be observed **automatically** in their world, and
2. What would be **self-reported only** — recorded by the working agent about
   itself, and labeled that way in every later finding.

Record the harness, the chosen observation plan, and model endpoints in
`profile/harness.md`. If nothing in `harness/` matches, use
`harness/fallback.md` and say plainly that observation will be weaker.

### Stage 4 — Pick the first task to observe

Ask for a real task coming up soon — a ticket they would do this week anyway.
Not a toy, not their hardest problem; a normal one. Agree on when they will do
it. Explain what observation will mean in their harness (from stage 3) and
that they should work exactly as they always do — the value of step 2 depends
on it. Record the choice in `profile/profile.md`.

Then close the interview: summarize the whole profile back in under ten
sentences, ask for corrections, and tell them what happens next (step 2 — and
if step 2 is not yet available in this version, say so and stop there; their
profile is safe and will be used when it lands).

## Files this step owns

- `workspace/profile/state.json` — progress marker. Format:
  `{"step": "1-interview", "stage": 2, "updated_utc": "2026-08-31T17:00:00Z"}`
  Stages: 0–4, then `"stage": "done"`.
- `workspace/profile/profile.md` — running answers, grouped by stage, each
  marked `(user)` or `(default)` for how it was decided.
- `workspace/profile/blast-radius.md` — the two tables from stage 1.
- `workspace/profile/harness.md` — stage-3 findings: harness, versions,
  endpoints, observation plan, what is automatic vs self-reported.

Create `workspace/profile/` on first write. Never write anywhere else.
