# Ledger formats

All ledgers are JSONL: one JSON object per line, appended, never rewritten.
Every row carries `"v": 1` (format version) and `"ts"` (UTC ISO-8601). Any
recorder — ours or a third party's — that claims a *measured* stream must
produce these rows, or rows that translate into them losslessly.

## model_calls.jsonl (one row per model/API call)

```json
{"v": 1, "ts": "2026-08-31T17:00:00.123+00:00", "seq": 1,
 "proxy": "local-llm", "method": "POST", "path": "/v1/chat/completions",
 "status": 200, "dur_ms": 843, "req_bytes": 2311, "resp_bytes": 512,
 "stream": false, "model": "qwen2.5-coder-32b",
 "tokens_in": 1201, "tokens_out": 88, "cache_read": null, "cache_write": null,
 "note": null}
```

- `tokens_*` null means usage was not visible — which the calibration canary
  must catch (requirement O2) before a real session.
- `note` carries parse caveats (`no-usage-in-response`,
  `client-disconnected`); a non-null note is a flag, not an error.

## actions.jsonl (one row per agent action)

```json
{"v": 1, "ts": "2026-08-31T17:00:01.000+00:00", "event": "PreToolUse",
 "session": "abc123", "tool": "Bash", "detail": "{\"command\": \"ls\"}"}
```

`detail` is scrubbed and truncated (600 chars); the point is *what kind of
action, on what*, not a transcript. For self-reported streams the working
agent appends the same shape with `"event": "self-report"`.

## capture/ (replay raw material — requirement O8)

One file per exchange: `000001_POST_v1_chat_completions.json`, holding the
scrubbed request and response (headers + body). These are the raw material
for frozen test fixtures later; they stay inside `workspace/`, which is
git-ignored, like everything else here.

## session.json (the manifest — one per observed session)

```json
{"v": 1, "started": "...", "ended": "...",
 "task": "PROJ-123: fix the retry loop",
 "repos": [{"path": "../their-project", "commit": "abc1234"}],
 "streams": [
   {"name": "model-calls", "recorder": "engine proxy", "evidence": "measured",
    "ledger": "ledgers/model_calls.jsonl"},
   {"name": "agent-actions", "recorder": "rules-file self-report",
    "evidence": "self-reported", "ledger": "ledgers/actions.jsonl"}],
 "gaps": [{"what": "CI logs", "why": "no access path", "approved_by_user": true}],
 "environment": {"os": "...", "harness": "...", "versions": {}}}
```

The manifest is where evidence labels (O7), acknowledged gaps (O10), and the
repo commits at task start live. Findings in step 3 cite it.

## calibration.json (one per calibration — requirement O9)

```json
{"v": 1, "ts": "...", "automated_probes": {"proxy": "pass", "hook": "pass"},
 "canary": {"ran": true, "streams_with_rows": ["model-calls", "agent-actions"],
            "tokens_visible": true, "secrets_found": false},
 "approved_gaps": [], "ready": true}
```

`"ready": true` is the recorder's license to run a real session. No file, or
`"ready": false` — no session.
