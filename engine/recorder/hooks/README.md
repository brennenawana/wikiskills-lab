# Claude Code hooks pack

Writes one ledger row per tool call of the observed agent — measured, not
self-reported — without changing the agent's behavior in any way
(`ledger_hook.py` exits 0 on every path, always).

## Install

Merge this into the observed project's `.claude/settings.json` (or the user's
`~/.claude/settings.json`), replacing `<LAB>` with the absolute path of this
repository and `<WS>` with the absolute path of `<LAB>/workspace`:

```json
{
  "hooks": {
    "PreToolUse": [
      {"hooks": [{"type": "command",
        "command": "python3 <LAB>/engine/recorder/hooks/ledger_hook.py <WS>/ledgers/actions.jsonl"}]}
    ],
    "PostToolUse": [
      {"hooks": [{"type": "command",
        "command": "python3 <LAB>/engine/recorder/hooks/ledger_hook.py <WS>/ledgers/actions.jsonl"}]}
    ],
    "Stop": [
      {"hooks": [{"type": "command",
        "command": "python3 <LAB>/engine/recorder/hooks/ledger_hook.py <WS>/ledgers/actions.jsonl"}]}
    ]
  }
}
```

On Windows, use `python` instead of `python3`. Remove the block after the
observed session — observation is a consented, bounded activity, not
surveillance.

## Verify before trusting (always)

```
python3 engine/recorder/probe.py hook
```

The probe feeds sample events through the script and checks: rows written,
fields present, secrets scrubbed, exit code 0. Then do one live check: start
the observed agent, ask it to read any file, and confirm a `PreToolUse` row
appears in `workspace/ledgers/actions.jsonl`. No row → fix before the real
session. The checklist rule applies to our own tools too.

## What this pack does NOT capture

Token spend. That comes from the session transcript or the recording proxy —
see `steps/2-observe/requirements.md` (requirement O2) for why a plan without
token visibility is incomplete.
