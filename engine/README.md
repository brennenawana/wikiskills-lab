# engine/ — the runnable parts

All standard-library Python (3.10+), no dependencies to install, same
behavior on macOS, Linux, and Windows. Nothing here is trusted until its
tests pass **on this machine**:

```
python3 engine/selftest.py            # meter, gateway, look ledger, runner
python3 engine/recorder/probe.py proxy
python3 engine/recorder/probe.py hook
```

| Component | What it does |
|---|---|
| `recorder/` | Observation: recording proxy, Claude Code hooks pack, and the probes that verify any recorder (step 2) |
| `budget/meter.py` | Fail-closed budget meter (checks caps BEFORE every spend; the append-only ledger is the truth) and the test-look ledger |
| `gateway/gateway.py` | One `call()` for every model backend: local OpenAI-compatible endpoints (Ollama/vLLM), Anthropic API, the Claude Code CLI on subscription login, and a free `canned` backend for dry runs. Sums every usage entry; bills the highest of independent cost accountings |
| `measure/runner.py` | Suite runner for baselines and every later measurement: meter-prechecked per task, checkpointed per task, summary recomputed from the results file (step 4) |
| `selftest.py` | The proof: 16 checks covering the failure modes that actually happened in the field (undercounted usage, budget breaches, double looks, lost work on interruption) |
