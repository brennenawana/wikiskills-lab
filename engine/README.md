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
| `recorder/` | Observation: recording proxy (record AND hermetic replay modes), Claude Code hooks pack, and the probes that verify any recorder (steps 2 and 5) |
| `budget/meter.py` | Fail-closed budget meter (checks caps BEFORE every spend; the append-only ledger is the truth) and the test-look ledger |
| `gateway/gateway.py` | One `call()` for every model backend: local OpenAI-compatible endpoints (Ollama/vLLM), Anthropic API, the Claude Code CLI on subscription login (agentic options: tools, workdir, streaming traces, JSON schema), and a free `canned` backend for dry runs. Sums every usage entry; bills the highest of independent cost accountings |
| `measure/runner.py` | Suite runner for baselines and every later measurement: meter-prechecked per task, checkpointed per task, summary recomputed from the results file (step 4) |
| `evolve/` | The evolution loop (step 5): the three storage layers (`wikistore.py`) and the loop with its strict-improvement gate, plateau stop, and two proposer modes — CLI ReAct and packet mode for any backend (`loop.py`) |
| `capsule/capsule.py` | Task capsules: pin repo commits, freeze fixture hashes, verify, and make disposable checkouts — never the live tree |
| `report/report.py` | Before/after report with the noise floor stated and a hard warning when suite versions differ |
| `journal.py` | The activity journal: append-only rows (stage, decision, artifact, install, ...) written at act time, secret-scrubbed, read back with `tail` so a session weeks later knows what happened last |
| `selftest.py` | The proof: 47 checks covering the failure modes that actually happened in the field (undercounted usage, budget breaches, double looks, lost work on interruption, gate leaks, a record that gets rewritten) |
