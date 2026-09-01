# Glossary

Every term of art used in this repository, one plain sentence each.

- **Agent** — a model that works in steps, using tools (reading files, running
  commands), instead of answering in one shot.
- **Harness** — the tool that runs your agent: Claude Code, Cursor, a script
  of your own.
- **Executor** — the model that does the actual work tasks.
- **Optimizer** — the model that studies failures and proposes skills; it can
  be the same model as the executor, or a stronger one.
- **Skill** — a text file of instructions the agent loads for a kind of task;
  the main thing the improvement loop produces.
- **Wiki** — the improvement loop's persistent notebook: knowledge it keeps
  between runs and never rolls back.
- **Trace** — the raw record of one task attempt, kept unchanged so failures
  can be studied later.
- **Ledger** — an append-only file of records (actions, costs); nothing in a
  ledger is ever edited or deleted.
- **Blast radius** — everything a task can touch: all repositories plus all
  outside services.
- **Engagement** — one improvement, start to finish: a chosen focus, its
  suite, its contract, its runs, its report; each lives in its own numbered
  folder and is frozen when finished.
- **Owner notes** — a file in a run's wiki where the human leaves hints for
  the optimizer roles; shown to them labeled as coming from the human.
- **Provenance header** — the note on every installed artifact saying which
  engagement produced it, on which suite version, and what it scored.
- **Activity journal** — `workspace/journal.jsonl`: the append-only record
  of what the coach did and when, one line per stage, decision, artifact,
  and install. A new session reads its last rows to say where the work
  stopped.
- **Coach skill** — the one skill that opens this repository from anywhere:
  inside the checkout it runs the coach, from the user's own project it
  captures "I want to improve X" and queues it in the inbox. Also called
  the **return path** when used that second way.
- **Task capsule** — a frozen, replayable copy of one real task: pinned
  repository versions plus recorded service data, so a test gives the same
  answer next month.
- **Task suite** — the set of test tasks used to measure a metric.
- **Metric** — the one number you and the coach agree to improve, defined
  before any improvement starts.
- **Baseline** — the metric's value today, measured before any change.
- **Scorer** — the code that turns one task attempt into a score, as
  mechanically as possible.
- **Validation split** — the small set of tasks used during the loop to decide
  whether to accept a proposal.
- **Held-out test** — tasks locked away during all improvement and scored only
  at the end; the only numbers worth quoting.
- **Seed** — one independent repeat of a whole run, starting fresh; several
  seeds show how much the result depends on luck.
- **Gate** — the accept/reject rule: a proposed skill is kept only if the
  validation score strictly improves.
- **Contract** — the written rules of an experiment (budgets, stop rules,
  statistics), frozen before the data exists.
- **Stop rule** — a pre-agreed condition that halts the work (a spend cap, a
  plateau), with its consequence written next to it.
- **Fail closed** — when a limit or a check cannot be verified, stop — never
  continue and hope.
- **Measured vs self-reported** — measured records come from logs, hooks, or
  recorded traffic; self-reported ones are the working agent's own claims
  about itself, and are labeled so they are never mistaken for measurements.
- **Recording proxy** — a small local pass-through placed in front of a model
  or service endpoint that writes down every request and response.
- **Baseline visibility** — the state this repository works to create first:
  knowing what your setup actually does, before changing anything.
