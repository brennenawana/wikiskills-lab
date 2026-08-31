# Harness

*(Format sample — see the folder README. Values are illustrations only.)*

- **Identified as:** custom pipeline (`harness/custom-pipeline.md`).
  Signals: user description; no agent instruction files found; model
  endpoint configured in `tools/run_ticket.py`.
- **Endpoints found (locations only, never credentials):**
  - model: `http://127.0.0.1:11434/v1` (Ollama)
  - tracker: `https://tracker.internal/rest/api/2/` (token in `.env`,
    fact recorded, value not)

## Observation plan

| Stream | Recorder | Evidence grade |
|---|---|---|
| model calls | recording proxy on port 8788; pipeline base URL changed to it | measured |
| tracker traffic | recording proxy on port 8789 in front of the tracker API | measured |
| agent actions | the pipeline is the agent here; its model and tracker traffic covers it | measured |
| CI | none — human-only web UI | acknowledged gap |

Told to the user honestly: everything the pipeline does passes through the
two proxies, so this setup gets full measurement with two config-line
changes. The CI gap was approved and is recorded in the session manifest.
