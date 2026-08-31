# Adapter — engine ↔ SpreadsheetBench

Wires the engine to the benchmark: task loading, the upstream checker at
its pinned commit, and the agentic executor (one CLI conversation per test
case, Bash tool only, isolated workdir, blind to the wiki).

## Setup

```
python3 ../fetch_data.py            # ~15 MB, checksum-verified
pip install "openpyxl==3.1.3" "pandas==2.2.0"   # the upstream's pins
python3 run.py verify               # data + checker + manifest sanity
```

`verify` must pass before anything else. It loads the frozen 30/15/100
manifest, imports the checker (refusing on a commit mismatch), and runs
the eligibility self-test on real tasks: the golden file must match
itself, and the input must not.

## Reproducing the experiment

Real runs need the Claude Code CLI on a logged-in subscription and real
quota — read `../CONTRACT.md` (budgets, look rules) and `../REPORT.md`
(what to expect, what it cost) first. Review `caps.json` (created with a
conservative $25 default on first run) before raising anything.

```
# one self-evolution run (cheap model optimizes itself)
python3 run.py evolve --run-name B-s1 --optimizer claude-haiku-4-5

# one frontier-guided run
python3 run.py evolve --run-name C-s1 --optimizer claude-opus-5

# held-out evaluation — spends a test look BEFORE running; one per source
python3 run.py eval --run-name eval-base --split test
python3 run.py eval --run-name eval-C-s1 --skills-from C-s1 --split test
```

Everything is metered fail-closed and checkpointed per task; an
interrupted command resumes where it stopped. Outputs land in
`../runs_local/` (git-ignored, like `../data/`).

A different machine is a different execution system: run the small
equivalence probe (the 15 validation tasks, no skills, both machines)
before comparing numbers across machines.
