# workspace/ — your private data

Everything the coach generates **for you** lands in this folder, and only here.
Git ignores all of it (this README is the one exception). Nothing in this
folder is ever committed, uploaded, or shared. Delete the folder and every
trace of your engagement is gone.

Work is organized into **engagements** — one chosen focus each, measured and
improved start to finish. Your profile and your observation records are
shared across engagements and only grow; each engagement's own files live in
its numbered folder and are frozen when it finishes.

| Folder | Contents | Written during |
|---|---|---|
| `profile/` | Interview answers, the map of your repos and services, your existing skill inventory, and `state.json` (where you are) | Step 1 |
| `ledgers/` | Records of observed work sessions: what was read, called, and spent. A growing pool — never reset | Step 2 |
| `capsules/` | Frozen copies of observed tasks, so tests stay repeatable while your real work moves on | Step 2 |
| `diagnosis/findings.md` | Findings from the ledger pool, updated as more sessions land | Step 3 |
| `inbox/` | Notes you queued from inside your own project (the coach skill); each becomes a candidate focus | Any time |
| `journal.jsonl` | The append-only record of what was done and when — one line per stage, decision, artifact, and install. Never edited | Any time |
| `engagements/<nnn-slug>/` | One engagement: `focus.md`, `suite/`, `contract/`, `runs/`, `REPORT.md` | Steps 3–5 |
| `skills/` | Record copies of adopted artifacts, each with a provenance header (which engagement, which suite version, what it scored) | Step 5 |

Two safety rules the coach follows everywhere: secret values (tokens, keys,
passwords) are never written into these files — only the fact that one
exists. And your own skill files and repositories are never modified without
your approval; installing an adopted artifact into your world is always an
explicit, approved step.
