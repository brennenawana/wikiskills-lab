# Suite format

`workspace/suite/suite.json` — the frozen measuring stick.

```json
{"v": 1, "name": "ticket-context", "version": "1",
 "metric": "tokens ingested per ticket, lower is better",
 "system": "optional system prompt used for every task",
 "max_tokens": 4096,
 "prices": {"qwen2.5-coder-32b": {"in": 0.0, "out": 0.0}},
 "tasks": [
   {"id": "t-001",
    "instruction": "the full task text the executor receives",
    "scorer": {"kind": "exact", "expected": "42"}},
   {"id": "t-002",
    "instruction": "...",
    "scorer": {"kind": "command",
               "command": "python3 checkers/check_t002.py",
               "timeout_s": 120}},
   {"id": "t-003",
    "instruction": "...",
    "scorer": {"kind": "token-budget", "max_tokens": 20000}}]}
```

## Scorer kinds (deterministic only)

| Kind | Passes when | Use for |
|---|---|---|
| `exact` | response text equals `expected` (whitespace-trimmed) | known single answers |
| `contains` | `expected` appears in the response | answers with one required fact |
| `command` | the command exits 0 (gets `TASK_OUTPUT` = path to the response text, `TASK_ID` in its environment) | real checkers: tests, diff comparators, ledger-threshold scripts |
| `token-budget` | tokens used (in + out) ≤ `max_tokens` | process metrics |

## Rules

- Task inputs must be **frozen**: files copied into the suite directory,
  or recorded captures — never a live system that will have moved on.
- `version` changes whenever any task or scorer changes, and numbers are
  comparable only within one version.
- Keep checker scripts under `workspace/suite/checkers/` so the whole
  measuring stick travels as one folder.

## Outputs (written by the runner)

- `workspace/runs/<name>/results.jsonl` — one row per task, appended as
  each finishes (interruptions lose nothing).
- `workspace/runs/<name>/summary.json` — mean score, per-task scores,
  total cost, error count; recomputed from the results file.
- `workspace/runs/<name>/spend.jsonl` — the meter's ledger for the run.
