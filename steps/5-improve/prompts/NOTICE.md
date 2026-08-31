# NOTICE — attribution for this directory

The three prompt files here are reproduced **word for word** from:

> Tang et al. (Google Research), *WikiSkill* — arXiv:2608.27454,
> Appendix E. Licensed under **CC BY 4.0**
> (https://creativecommons.org/licenses/by/4.0/).

- `inference-agent-spreadsheetbench.txt` — Appendix E.1
- `wiki-maintainer.txt` — Appendix E.2
- `skill-proposer.txt` — Appendix E.3

Changes: none to the text itself. The files keep the paper's template
placeholders (`{skill_section}`, `{task_desc}`), which the engine fills by
string replacement. Environment-specific tool-mapping notes are appended at
run time by `engine/evolve/loop.py` and are our own text, not the paper's.

If you redistribute these files, keep this notice with them.
