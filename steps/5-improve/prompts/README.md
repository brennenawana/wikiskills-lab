# Role prompts

The system prompts of the evolution loop's roles, verbatim from the
WikiSkill paper (see `NOTICE.md` for license and attribution).

- `wiki-maintainer.txt` and `skill-proposer.txt` are **generic** — the
  engine loads them for every task family. The proposer keeps a
  `{task_desc}` placeholder the engine fills with your task family's
  one-line description.
- `inference-agent-spreadsheetbench.txt` is **task-family-specific**: it is
  the executor prompt for spreadsheet tasks, used by
  `benchmarks/spreadsheet/`. Your own task family gets its own executor
  prompt (usually your existing agent setup, unchanged — the loop improves
  the skills injected into `{skill_section}`, not the base prompt).

Engine rule: placeholders are filled with `.replace()`, never `.format()` —
the prompts contain literal JSON braces that `.format()` would mangle.
