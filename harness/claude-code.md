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

## Notes for later steps

- Improvement artifacts install as `CLAUDE.md` edits, skill files, and hook
  or settings changes — all text, all diffable.
- Specialized guidance grows in this file as the observe step lands.
