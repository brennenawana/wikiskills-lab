# Findings

*(Format sample — see the folder README. Every number below is an
illustration of what a finding looks like, not a record of a real
session.)*

## F1 — The tracker pull brings in far more than the task uses

- **What:** the pipeline fetched the ticket, all its comments, and every
  linked ticket in full; the prompt carried roughly ninety thousand tokens
  of tracker text, and the diff only used material from the ticket itself
  and one linked ticket.
- **Evidence:** `ledgers/tracker_calls.jsonl` rows 2–9 (eight fetches, one
  per linked ticket); `ledgers/model_calls.jsonl` row 1 (prompt size).
- **Grade:** measured.
- **Size:** repeats on every ticket → largest single cost in the session,
  and it grows as the tracker history grows.

## F2 — The same shared-library file was refetched four times

- **What:** the pipeline rebuilt its context from zero on each model call,
  re-reading the same `orbit-shared` module every time.
- **Evidence:** `ledgers/model_calls.jsonl` rows 1, 3, 4, 6 (same file
  content visible in the request captures).
- **Grade:** measured.
- **Size:** moderate; a fixed multiplier on every multi-call task.

## F3 — Internal function called with wrong parameters on the first try

- **What:** the user reports the model regularly writes calls to their own
  helpers with invented parameters, and they fix these by hand before the
  PR.
- **Evidence:** the user's own account during the interview; one hand-fix
  was seen in this session's diff.
- **Grade:** self-reported (one supporting observation). If chosen, the
  first move is to measure it properly: count
  functions-wrong-on-first-write from diffs over several tasks.

*No other patterns rose above noise in one observed session. One session
is thin evidence — a second observed ticket would firm up F1 and F2.*
