# Sample artifacts — what your files will look like

This folder shows the **format** of everything steps 1–3 write into your
`workspace/`, filled in for an imaginary generic setup (a two-repo API
project, a ticket tracker, a local model behind a pipeline script).

**Every value in this folder is an illustration of format. None of it is a
record of anything that happened.** This repository does not publish
invented results — for a real end-to-end record with real numbers, read
`benchmarks/spreadsheet/`.

| File | Written by | What it is |
|---|---|---|
| `profile/profile.md` | Step 1 | Interview answers, each marked (user) or (default) |
| `profile/blast-radius.md` | Step 1 | Every repo and outside service a task can touch |
| `profile/harness.md` | Step 1 | The identified harness and the observation plan, with honest evidence grades |
| `profile/state.json` | Every step | Where you are; any new session resumes from it |
| `ledgers/session.json` | Step 2 | The session manifest: streams, grades, gaps, repo pins |
| `ledgers/calibration.json` | Step 2 | Proof the recorder was verified before the real session |
| `diagnosis/findings.md` | Step 3 | Findings with evidence, grade, and weekly size (shared across engagements) |
| `diagnosis/focus.md` | Step 3 | The one chosen focus and the first metric sketch — in a real workspace this lives at `engagements/<nnn-slug>/focus.md` |
| `contract/CONTRACT.md` | Step 4 | The generated rules, filled in and ready for approval — in a real workspace, `engagements/<nnn-slug>/contract/CONTRACT.md` |

The raw ledger files themselves (`model_calls.jsonl`, `actions.jsonl`) are
not repeated here — their row formats, with examples, are in
`steps/2-observe/ledger-format.md`.
