# Step 3 — Diagnose

**Goal:** turn the step-2 ledgers into a small set of honest findings, and
end with ONE chosen focus, written down, that step 4 will build a measuring
stick for.

Inputs: `workspace/ledgers/` (the streams) and `workspace/ledgers/
session.json` (the manifest with evidence labels). No ledgers → go back to
step 2; diagnosis without observation is opinion.

## Stage 1 — Extract findings

Read the ledgers and write `workspace/diagnosis/findings.md`. Each finding
is four lines:

- **What:** one plain sentence. ("The tracker integration pulled every
  linked ticket in full — about 100K tokens — on a task that used two of
  them.")
- **Evidence:** the numbers and where they come from (ledger file, row
  range, counts). Never a vibe.
- **Grade:** `measured` or `self-reported`, copied from the stream's label
  in the manifest. A self-reported finding says so in its first sentence.
- **Size:** what it costs per week if it repeats (tokens, money, redone
  work), computed where possible, marked "rough" where not.

Look for the usual suspects: context pulled in but never used; the same
files re-read many times; token spend concentrated in one step; retries and
corrections after wrong first attempts; long human interventions at the
same spot; calls to services that returned nothing useful.

Honesty rules: do not pad the list — three strong findings beat ten weak
ones. Do not diagnose what the ledgers cannot support. An empty diagnosis
("the session looked healthy; here is what we could not see") is a valid
and useful result.

## Stage 2 — The user's own goal wins

If the interview recorded something the user already wants to improve
(their words, stage-2 question 9), or `workspace/inbox/` holds notes they
queued from daily work, those go first, whatever the ranking says. Show them what the ledgers say about it — supporting, neutral, or
"we saw no evidence of this, want to observe another task before choosing?"
— and let them decide with that in view.

## Stage 3 — Rank the candidates

If the user wants a recommendation, score each finding with `scoring.md`
and present **at most three** candidates, best first, each with one
paragraph: what would improve, how it would be measured, what it would
take. Name your recommendation in the first line. Never present a menu
without a default.

## Stage 4 — Choose and open the engagement

The user picks (or says "you pick" — then your recommendation stands,
recorded as a default). The chosen focus opens a new **engagement**:
create `workspace/engagements/<nnn-slug>/` (next number, short plain
slug — for example `001-tracker-context`) and write `focus.md` inside it:

- The focus, in one sentence the user agreed to.
- Why (the finding and its evidence, linked by file and row; or the inbox
  note, quoted).
- A first sketch of the metric (step 4 will make it exact).
- What kind of improvement artifacts are likely (skill file, context
  policy, pipeline config, instruction-file change).

If an inbox note led here, mark that note processed (move it into the
engagement folder). Update `state.json` — `"step": "3-diagnose",
"stage": "done", "engagement": "<nnn-slug>"` — then tell the user what
happens next: step 4, the measuring stick. Everything from here through
step 5 lives in this engagement's folder; finished engagements are never
edited.
