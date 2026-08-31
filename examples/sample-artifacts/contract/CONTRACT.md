# Measurement Contract — tracker-context (v1, frozen on approval)

*(Format sample — see the folder README. This shows the template from
`steps/4-measure/contract-template.md` filled in for the imaginary setup.
Thresholds and budgets here are pre-registered settings, not results.)*

> Rules written before the data. After approval, nothing above the
> amendment log changes; corrections are appended there, each one dated
> and approved by the owner.

## 1. Question and metric

- Focus: cut what the tracker pull adds to the prompt, without losing
  anything the task needs.
- Metric: tracker tokens carried into the prompt per ticket, lower is
  better. Guard metric: suite tasks must still pass their checkers.
- Decision this measurement drives: whether the new fetch policy replaces
  the current pull-everything behavior in the pipeline.

## 2. Frozen measuring stick

- Suite: `workspace/suite/suite.json`, version 1, 8 tasks (replayed from
  frozen capsules of observed tickets), SHA-256 `<64-hex hash>`.
- Held-out part: none — this is a before/after process measurement, both
  runs on the full frozen suite.
- Scorers: `token-budget` (the metric) plus `command` checkers (the
  guard). No scorer changes within a suite version.

## 3. Models and environment

- Executor: the local ~30B model via Ollama (OpenAI-style endpoint),
  driven by the pipeline in replay mode against capsule fixtures.
- Optimizer: same model, packet mode (fully local tier — the contract
  therefore prescribes more attempts and conservative stops).
- Environment identity: recorded per `ledgers/session.json`.

## 4. Budgets — every limit names its consequence

Unit: **tokens** (own GPU; no per-token cost, but consumption is still
governed). Projection per task: measured from the dry run and two real
calls.

| Scope | Limit | On breach |
|---|---|---|
| per run | 2,000,000 tokens | run stops; checkpointed; owner note to resume |
| total (this engagement) | 10,000,000 tokens | full stop; raising it is an amendment below |

The meter checks BEFORE every call and fails closed.

## 5. Looks at held-out tasks

No held-out part; every measurement is a full-suite run, recorded in the
run ledger.

## 6. Stop rules

| Rule | Condition | Consequence |
|---|---|---|
| Budget | any §4 limit | as named in §4 |
| Headroom | baseline guard-pass rate = 0% | suspect the scorers; rescope under a new suite version |
| Plateau (step 5) | 3 consecutive rejected proposals | stop the loop; report |
| Integrity | ledger gap, scorer error, replay miss | halt and diagnose |

## 7. Reading the result (written before the data)

- **Improved:** tracker tokens per ticket down at least 40% AND the guard
  pass rate not lower than baseline → adopt the fetch policy.
- **No effect / worse:** roll back; the baseline stands; record what was
  tried.
- With 8 tasks, one task flipping moves a mean by 12.5 points — treat
  guard-rate changes smaller than that as noise.

## 8. Roles

- Owner: the developer — approves this contract, amendments, any raise.
- Executor of the contract: the agent sessions running the steps.

## 9. Approval record

- Presented in plain words on 20XX-01-16; approved 20XX-01-16.
- Frozen: hashes recorded in `workspace/contract/binding.json`.

## 10. Amendment log (append-only)

- (none yet)
