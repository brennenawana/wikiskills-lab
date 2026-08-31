# Credits

This repository packages published research into a usable tool. The ideas
below are borrowed with thanks; the mistakes are ours.

## Method

- **WikiSkill** — Tang et al., Google Research, 2026.
  [arXiv:2608.27454](https://arxiv.org/abs/2608.27454).
  The skill-evolution loop this repository implements: three layers (raw
  traces, a persistent wiki, gated skills), four roles, and the accept-only-on-
  strict-improvement rule. The role prompts used by our improvement step are
  word-for-word from the paper's Appendix E, licensed **CC BY 4.0**; a NOTICE
  file accompanies them where they appear.
- **"LLM Wiki"** — Andrej Karpathy's gist sketching persistent, self-edited
  agent knowledge. Lineage for the wiki layer.
- **karpathy/autoresearch** — the small-scale, fixed-budget experiment shape
  (few directories, one metric, hard caps) that our case study follows.

## Case study (benchmarks/spreadsheet/)

- **SpreadsheetBench** — Ma et al., NeurIPS 2024 — the tasks and the checker,
  via the "Verified-400" subset (Hugging Face: KAKA22). The upstream project
  publishes no license file, so this repository stores none of its data or
  code; our fetch script downloads both from the original sources at pinned
  versions.
- **microsoft/SkillOpt** — the published task-id splits our draw nests inside.
- Models used in the case study: Claude Haiku 4.5 and Claude Opus 5
  (Anthropic), driven through the Claude Code CLI.

## A note on references

Every concept in this repository is meant to stand on its own — if you find a
reference that leads nowhere, that is a bug; please open an issue.
