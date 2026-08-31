# Step 5 — Improve

**Status: not yet available in this version.** Tell the user so, plainly, and
stop here.

What this step will do: run the evolution loop — the WikiSkill method this
repository is named for (see `CREDITS.md`). The loop proposes improvements as
text: skills, instruction-file changes, tool policies, configuration. Each
proposal is tested against the step-4 suite and kept only if the score
strictly improves; anything that loses is rolled back. It runs inside the
budgets and stop rules the user approved in step 4, with spending metered
before every call. The output: a before/after number the user helped define,
the winning artifacts installed into their daily work, and light ongoing
monitoring. For a complete real example of this loop running — rules, costs,
results — see `benchmarks/spreadsheet/`.
