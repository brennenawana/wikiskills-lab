# Harness: Claude Code

## Recognize it

- The user says so; `claude` is on PATH; the project has a `CLAUDE.md` it
  honors; session transcripts exist under `~/.claude/projects/`.

## What observation will look like (step 2)

Strongest case. Everything is **measured**:

- **Hooks** (PreToolUse/PostToolUse/Stop) can write one ledger line per tool
  call — file reads, commands, service calls — without changing the agent's
  behavior.
- **Session transcripts** (JSONL) carry per-call token usage for spend
  ledgers.

Tell the user: observation is automatic here; they work exactly as normal.

## Concretely

- Actions: install the hooks pack — `engine/recorder/hooks/README.md`.
- Token spend: session transcripts, or route API-mode traffic through the
  recording proxy.
- Verify first, always: `python3 engine/recorder/probe.py hook`, then the
  live canary in `steps/2-observe/probes.md`.

## Notes for later steps

- Improvement artifacts install as `CLAUDE.md` edits, skill files, and hook
  or settings changes — all text, all diffable.
