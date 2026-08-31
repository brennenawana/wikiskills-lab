# Profile

*(Format sample — see the folder README. Values are illustrations only.)*

## Stage 2 — How they work

- **Harness:** a pipeline script of their own — `tools/run_ticket.py` takes
  a ticket id, builds a prompt, and sends it to the model. (user)
- **Model:** a ~30B coding model served locally by Ollama at
  `http://127.0.0.1:11434/v1`. (user)
- **Cost reality:** own GPU; no per-token cost. Budgets will be in
  **tokens**, not dollars. (user)
- **A typical task, their words:** "A ticket comes in, I run the script,
  it makes a branch and a diff. I read the diff. Maybe half the time I fix
  something by hand before I open the PR."
- **How quality is judged today:** "I read it and use my judgment." (user)
- **What already bothers them:** "The model seems to know the whole
  tracker history but still gets our internal functions wrong. And it
  feels slow to start." (user, recorded before any measurement)

## Stage 4 — First observed task

- Chosen task: the next ordinary ticket in the queue (a bug fix in the
  request-retry code). (default — the user said "you pick")
- Scheduled: this week, worked exactly as normal.
