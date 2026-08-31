# Step 2 — Observe

**Goal:** record one or more of the user's real tasks, done the normal way,
into durable ledgers — and prove the recording works **before** the real
session, so no observed work is ever wasted.

This step has strong opinions and loose tools. The opinions are the
checklist in `requirements.md` (read it first — it is short). The tools are
whatever passes it: our components in `engine/recorder/`, the harness's own
logs, or tools the user already has. Implementation varies by project and
operating system; the checklist does not.

## Stage 1 — Plan the streams

From `workspace/profile/` (step 1), list what must be recorded:

- **Model calls** — always.
- **Agent actions** (files read, commands run) — always.
- **Outside services** in the blast radius (tracker, CI, ...) — each one is
  either a stream or an explicit gap the user approves (requirement O10).

For each stream, pick a recorder, starting from the harness note in
`harness/` (it names the strongest option for their world) and the user's
own tools. Write the plan as a coverage table: streams × O1–O10, each cell
`yes` / `no` / `unknown`.

## Stage 2 — Evaluate, and reject what fails

If the user proposes their own tooling, apply the acceptance rule in
`requirements.md` exactly: probe the unknowns, never take a brochure's word,
and if a MUST fails and cannot be fixed, **reject the tool politely and
suggest the nearest working alternative**. Gaps that remain get labels, not
silence.

## Stage 3 — Build and configure

Typical assemblies (details in each component's own docs):

- **Recording proxy** (`engine/recorder/proxy.py`) — one instance per
  endpoint: the model server, the tracker API. The user points the client's
  base URL at it. Works for any OpenAI-style or Anthropic-style endpoint and
  any plain HTTP API; stdlib Python, all platforms. Use `--capture` so the
  session also collects replay raw material (O8).
- **Claude Code hooks pack** (`engine/recorder/hooks/`) — measured action
  rows for Claude Code users.
- **Self-report snippet** — for harnesses with no measurable path: add to
  the harness's rules file: *"After every significant action (file read,
  command, service call), append one JSON line to `<workspace>/ledgers/
  actions.jsonl`: `{"v":1,"ts":"<UTC>","event":"self-report","tool":"...",
  "detail":"..."}`. Never write secret values."* Label the stream
  self-reported (O7).

## Stage 4 — Calibrate (the gate)

Run the probes, then the live canary, exactly as `probes.md` describes, and
write `workspace/ledgers/calibration.json`. **No real session until it says
`"ready": true`.** This stage is minutes; a broken recorder discovered after
a real session costs the session.

## Stage 5 — Record the real task

1. Note the current commit of every blast-radius repo into the session
   manifest (`session.json`) — this is what later makes the task replayable.
2. Start the recorders. Confirm to the user: *"Recording is on. Work exactly
   as you always do; I will stay out of the way."* Do not coach, interrupt,
   or comment during the session — observed work must stay normal work.
3. When the user says the task is done (or abandoned — abandonment is data
   too), stop the recorders.

## Stage 6 — Close out

1. Complete `session.json`: streams, evidence labels, gaps, environment,
   start/end times.
2. Sanity-pass the ledgers: row counts per stream, total tokens, obvious
   holes. Report one honest paragraph to the user: what was captured, what
   was not, and roughly what the task cost.
3. Update `state.json` (`"step": "2-observe", "stage": "done"` — or bump a
   session counter if more tasks will be observed; two or three observed
   tasks make step 3 much stronger).
4. Tell the user what happens next: diagnosis (step 3) — and if it is not
   yet available in this version, say so and stop. The ledgers are safe and
   waiting.

## Files this step owns

- `workspace/ledgers/model_calls.jsonl`, `actions.jsonl`, service ledgers —
  the streams (`ledger-format.md`).
- `workspace/ledgers/capture/` — scrubbed raw exchanges (O8).
- `workspace/ledgers/calibration.json` — proof the recorder was verified.
- `workspace/ledgers/session.json` — the manifest findings will cite.
