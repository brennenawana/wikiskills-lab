# Harness: Cursor (and similar IDE agents)

## Recognize it

- The user says so; the project has a `.cursorrules` or Cursor-style rules
  files; work happens inside the IDE.

## What observation will look like (step 2)

Mixed, and say so honestly:

- Cursor exposes no public hook system, so tool-level activity cannot be
  measured from outside.
- If the model traffic can be routed through a configurable endpoint, our
  recording proxy can measure every model call, its size, and its cost
  (**measured**).
- Everything else is **self-reported**: the rules file instructs the working
  agent to append one line per significant action to a ledger. Self-reported
  records are labeled in every finding built on them.

## Notes for later steps

- Improvement artifacts install as rules-file edits and prompt/policy text.
- The plan faces the checklist and probes in `steps/2-observe/` like every
  other setup; the self-report stream uses the snippet in the step-2 GUIDE.
