# Probe catalog

How each requirement in `requirements.md` gets **demonstrated** before a real
observed session. Three kinds of probe, cheapest first:

1. **Automated** — `engine/recorder/probe.py` runs it for you, against a fake
   upstream: no real credentials, no network, no spend.
2. **Live canary** — one tiny scripted exchange through the real setup, with
   known expected ledger rows.
3. **Inspection** — a fact you check once and record (file paths, settings).

## Automated probes (run these first, always)

```
python3 engine/recorder/probe.py proxy    # the recording proxy
python3 engine/recorder/probe.py hook     # the Claude Code hook script
python3 engine/recorder/probe.py ledger --file <path>
                                          # any third-party tool's ledger
```

What they prove:

| Command | Requirements covered |
|---|---|
| `probe.py proxy` | O1 (row per call) · O2 (tokens, both API styles, plus SSE streams) · O3 (byte-identical passthrough) · O4 (append-only, durable) · O5 (timestamps, order) · O6 (planted fake secrets must not reach disk) · O8 (captures written) |
| `probe.py hook` | O1 · O5 · O6 · O3 (the hook exits 0 on every path, even fed garbage — it can never block the agent) |
| `probe.py ledger` | O4 · O5 · O6 — **format only**; it says so in its output. A third-party tool still needs the live canary below for O1/O2/O3. |

Non-zero exit = not ready. Do not argue with the probe; fix and re-run.

## The live canary (before every real session)

The automated probes prove the parts we ship. The canary proves the
**assembled system** — your endpoints, your settings, your machine, today.

1. Arm every recorder exactly as the real session will run.
2. Perform one tiny scripted task through the real setup. For example: ask
   the observed agent to read one named file and answer one question that
   costs a few hundred tokens; if a tracker is in the blast radius, have the
   pipeline fetch one known ticket.
3. Check the expectations, stream by stream:
   - **O1:** every action you just performed has its row — count them.
   - **O2:** the model-call rows show non-null token counts. A null here
     means usage is hidden (often a streaming setting) — fix it now, not
     during the real session.
   - **O10:** every stream in the plan produced at least one row. A stream
     with zero rows during a canary that touched it is a dead recorder.
   - **O6:** search the ledgers for any credential fragment you know is in
     use. Finding one is a full stop.
4. Record the result in `workspace/ledgers/calibration.json` (see
   `ledger-format.md`): what ran, which probes passed, which gaps the user
   approved. The real session may start only when this file says so.

## Inspection checks

- **O4:** ledger files live under `workspace/ledgers/` (or another path the
  user chose that is outside every observed repository and any conversation
  context), and the recorder opens them append-only.
- **O7:** the session manifest labels every stream `measured` or
  `self-reported` before the session starts.
- **O10:** read `workspace/profile/blast-radius.md` and check every row of
  it appears in the plan — as a stream or as an acknowledged gap.

## When a probe fails

Say what failed in one sentence, what that means in one sentence, and the
smallest fix. Examples:

- *Tokens null on streams* → "Your endpoint hides usage when streaming.
  Enable usage in stream responses, or route through the recording proxy."
- *Third-party tool has no readable ledger* → REJECT per the acceptance
  rule; offer the proxy or a labeled self-report plan.
- *Secret found in a ledger* → stop, delete the affected files, fix
  scrubbing, re-run all probes from the top.

A failed probe before the session is a cheap, private correction. The same
discovery after the session invalidates the data and wastes the user's time
— which is why O9 is a MUST and not advice.
