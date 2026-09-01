# Contract template

The agent fills this template into `workspace/engagements/<current>/contract/CONTRACT.md` in
stage 5 of the step-4 guide, then walks the user through every section in
plain words. The user approves; the file freezes; afterwards only the
amendment log changes. Replace every `{{...}}`; delete nothing else.

For a fully worked real example of a frozen contract with amendments, see
`benchmarks/spreadsheet/CONTRACT.md`.

---

# Measurement Contract — {{FOCUS_NAME}} (v1, frozen on approval)

> Rules written before the data. After approval, nothing above the
> amendment log changes; corrections are appended there, each one dated
> and approved by the owner.

## 1. Question and metric

- Focus: {{ONE_SENTENCE_FOCUS — from workspace/engagements/<current>/focus.md}}
- Metric: {{ONE_SENTENCE_METRIC — definition, direction, unit}}
- Decision this measurement drives: {{WHAT_THE_USER_WILL_DO_WITH_THE_NUMBER}}

## 2. Frozen measuring stick

- Suite: `workspace/engagements/<current>/suite/suite.json`, version {{V}}, {{N}} tasks,
  SHA-256 `{{SUITE_HASH}}`.
- Held-out part: {{TASK_IDS_OR_"none — before/after measurement only"}}.
- Scorers: {{LIST_SCORER_KINDS}}. No scorer changes within a suite
  version; a scorer change is a new version and a new baseline.

## 3. Models and environment

- Executor: {{MODEL, WHERE_IT_RUNS, BACKEND_KIND}}.
- Optimizer (step 5, if planned): {{MODEL_OR_"same as executor"}}.
- Environment identity: {{OS, HARNESS+VERSION, KEY_TOOL_VERSIONS}}.
  A different machine is a different execution system — re-baseline
  before comparing across machines.

## 4. Budgets — every limit names its consequence

Unit: {{USD | tokens | gpu-minutes — the user's own cost reality}}.
Projection per task: {{MEASURED_VALUE}} (measured from
{{DRY_RUN_PLUS_N_PRICED_CALLS}}, not guessed).

| Scope | Limit | On breach |
|---|---|---|
| per run | {{X}} | run stops; checkpointed; owner note to resume |
| total (this engagement) | {{Y}} | full stop; raising it is an amendment below |

The meter checks BEFORE every call and fails closed. A budget stop is a
finding about cost — reported, never quietly raised.

## 5. Looks at held-out tasks

{{IF_HELD_OUT: "One look per {{run/variant}}, planned here: {{LIST}}.
Each look is written to workspace/engagements/<current>/runs/looks.jsonl before its evaluation
starts. Any unplanned look downgrades the affected comparison to
INCONCLUSIVE." ELSE: "No held-out part; every measurement is a full-suite
run, recorded in the run ledger."}}

## 6. Stop rules

| Rule | Condition | Consequence |
|---|---|---|
| Budget | any §4 limit | as named in §4 |
| Headroom | baseline ≥ {{HI}}% or = 0% | rescope under a new suite version |
| Plateau (step 5) | {{K}} consecutive rejected proposals | stop the loop; report |
| Integrity | ledger gap, scorer error, unplanned look | halt and diagnose; a broken measurement is not evidence |

## 7. Reading the result (written before the data)

- **Improved:** {{THRESHOLD — e.g. "+X points on the suite" or "−Y% tokens
  per task"}} met on {{THE_HELD_OUT_PART_OR_FULL_SUITE}} → adopt the
  artifacts; keep monitoring.
- **No effect / worse:** threshold not met → roll back all artifacts;
  record what was tried; the baseline stands.
- With {{N}} tasks, single-task flips move the mean by {{100/N}} points —
  treat differences smaller than {{FLOOR}} as noise, whatever direction
  they point. {{IF_N>=30: "A paired comparison across the same tasks will
  accompany the point estimate."}}

## 8. Roles

- Owner: {{USER_NAME}} — approves this contract, amendments, and any
  raise of any limit.
- Executor of the contract: the agent sessions running the steps. They
  follow the written rules and do not change them mid-run.

## 9. Approval record

- Presented to the owner in plain words on {{DATE}}; approved on {{DATE}}.
- Frozen: hashes recorded in `workspace/engagements/<current>/contract/binding.json`.

## 10. Amendment log (append-only)

- (none yet)
