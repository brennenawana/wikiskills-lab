# Question bank — Step 1

Ask in your own words; these are purposes with example phrasings, not a
script. Skip any question whose purpose is already met. `Rec:` is what to do
when the user says "you pick."

## Stage 1 — Project map

1. **Purpose: locate the work.**
   "Point me at your project. Which folder is the main repository?"
2. **Purpose: complete the repository list.**
   "Are there other repositories this work touches — libraries you also edit,
   a deploy repo, infrastructure code?" Probe once: tasks often touch a second
   repo the user forgets to name.
3. **Purpose: list outside services.**
   "When a normal task goes from 'assigned' to 'done', which services are
   involved? Ticket tracker, CI, code review, cloud, anything else?"
4. **Purpose: agent reach.**
   "Which of those does your agent touch by itself — and which only you touch?"
   Rec: assume the agent touches only the repos, until observed otherwise.

## Stage 2 — How they work

5. **Purpose: identify the harness.**
   "Which tool runs your agent? (Claude Code, Cursor, a script of your own,
   something else?) How do you start it?"
6. **Purpose: identify models and cost reality.**
   "Which model does the work, and where does it run — your own machine, a
   subscription, a paid API? Roughly what does it cost you today?"
   This decides budgets and discovery-model choices later. If they run a local
   model, get the serving endpoint kind (Ollama, vLLM, other) and the model
   size class.
7. **Purpose: capture the normal workflow.**
   "Walk me through the last ordinary task you finished with the agent — from
   where it arrived to how you decided it was done."
8. **Purpose: how quality is judged today.**
   "How do you currently tell a good agent result from a bad one?" ("I read it
   and use my judgment" is a common and acceptable answer — record it.)
9. **Purpose: their pain, their words.**
   "What already bothers you about how this works?" Record verbatim. If they
   have a clear improvement wish, note it — in step 3 the user's own goal
   outranks anything we rank.

## Stage 4 — First observed task

10. **Purpose: choose a normal, real, near-term task.**
    "Pick a real task you would do this week anyway — an ordinary one, not
    your hardest." Rec: the next ticket in their queue.
11. **Purpose: schedule it.**
    "When will you do it? I only need you to work exactly as you always do."

## Questions NOT to ask

- Anything you can detect: installed CLIs, instruction files, repo layout
  (stage 3 checks these itself, with the user's consent from stage 0).
- Secret values. Never ask for a token, key, or password — only whether one
  exists and where it is configured.
- More than one "anything else?" per stage.
