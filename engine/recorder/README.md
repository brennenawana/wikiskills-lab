# engine/recorder — the reference recorders

Components that pass the Observability Checklist
(`steps/2-observe/requirements.md`). They are the defaults, not the law: any
tool that passes the same checklist, proven by the same probes, is equally
welcome.

| File | What it does |
|---|---|
| `proxy.py` | Recording proxy: sits in front of one HTTP endpoint (model server, tracker API), forwards everything unchanged, writes one ledger row per call with token usage, and optionally captures full scrubbed exchanges for later replay. Stdlib Python, macOS/Linux/Windows. |
| `hooks/` | Claude Code hooks pack: one measured ledger row per tool call of the observed agent. |
| `probe.py` | The miniature tests that prove a recorder works on this machine — ours or anyone's. Non-zero exit means "not ready". |

Quick start:

```
# prove the components work here (no credentials, no network, no spend)
python3 engine/recorder/probe.py proxy
python3 engine/recorder/probe.py hook

# then record: one proxy per endpoint
python3 engine/recorder/proxy.py \
    --upstream http://127.0.0.1:11434 --port 8788 --name local-llm \
    --ledger workspace/ledgers/model_calls.jsonl \
    --capture workspace/ledgers/capture
```

Point the client's base URL at `http://127.0.0.1:8788` and work normally.
Formats: `steps/2-observe/ledger-format.md`. The full step flow, including
the calibration gate that must pass before any real session:
`steps/2-observe/GUIDE.md`.
