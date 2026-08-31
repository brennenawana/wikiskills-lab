# Harness: Codex CLI (and similar AGENTS.md-reading CLIs)

## Recognize it

- The user says so; `codex` (or a similar CLI) is on PATH; the project honors
  `AGENTS.md`.

## What observation will look like (step 2)

- These CLIs let you configure the model base URL, so the model traffic can
  run through our recording proxy: every call, its size, its cost —
  **measured**.
- Tool-level activity (file reads, commands) is captured from the CLI's own
  logs where available, otherwise **self-reported** via the rules file, and
  labeled as such.

## Notes for later steps

- Improvement artifacts install as `AGENTS.md` edits and configuration.
- Specialized guidance grows in this file as the observe step lands.
