# Ranking rubric

Score each candidate 1–5 on three axes. Rank by the product
(M × I × E). Ties go to the more measurable candidate — a smaller
improvement you can prove beats a larger one you cannot.

## M — Measurability (can we count it?)

- **5** — a machine can score it from ledgers, tests, or file diffs, with
  no human in the loop. (Token spend per ticket; tests pass; functions
  wrong on first write, counted from diffs.)
- **3** — countable with a light, fast human check per task.
- **1** — only judgment ("the answers feel better"). A candidate scoring 1
  here is not eligible until someone finds a harder proxy for it.

## I — Expected impact (what does it save per week?)

- **5** — pays on every task: a cost or failure that appears in most
  observed tasks. (Indiscriminate context ingestion; a wrong-first-write
  pattern that forces rework daily.)
- **3** — pays on a class of tasks that recurs weekly.
- **1** — rare tasks, or savings too small to notice.

Ground this in the finding's **Size** line, not in enthusiasm.

## E — Effort (how cheap is the whole loop?)

- **5** — metric, task suite, and plausible improvements are all days of
  work; scorers are mechanical; tasks come straight from observed work.
- **3** — some scorer or suite construction work; still one engagement.
- **1** — weeks of setup before the first measurement. (Often a sign to
  narrow the focus, not abandon it.)

## Rules

- Present at most **three** candidates, best first, recommendation named.
- The user's own stated goal always appears, whatever it scores — shown
  with its scores and what the ledgers say about it.
- A `self-reported` finding can be a candidate, but say so: "if chosen, the
  first move is to measure it properly."
