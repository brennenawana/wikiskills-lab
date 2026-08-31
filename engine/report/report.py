#!/usr/bin/env python3
"""Before/after report generator.

Takes two run summaries (the frozen baseline and the run after
improvements) and writes one plain-language report the user can keep or
share. Numbers only from the summary files; nothing invented.

  python3 report.py --before workspace/runs/baseline/summary.json \
      --after workspace/runs/after/summary.json \
      --out workspace/runs/REPORT.md \
      [--metric "tasks solved on first attempt, higher is better"] \
      [--artifacts skill_a skill_b]

Standard library only.
"""

import argparse
import datetime
import json


def generate(before, after, metric=None, artifacts=None, noise_floor=None):
    n_b, n_a = before.get("n_tasks", 0), after.get("n_tasks", 0)
    same_suite = (before.get("suite") == after.get("suite")
                  and before.get("suite_version") == after.get(
                      "suite_version"))
    mean_b = before.get("mean_score") or 0.0
    mean_a = after.get("mean_score") or 0.0
    delta = (mean_a - mean_b) * 100
    cost_b, cost_a = before.get("total_cost", 0), after.get("total_cost", 0)

    per_b = before.get("per_task", {})
    per_a = after.get("per_task", {})
    improved = sorted(t for t in per_a
                      if per_a[t] > per_b.get(t, 0))
    regressed = sorted(t for t in per_a
                       if per_a[t] < per_b.get(t, 0))

    lines = [
        "# Before / After Report",
        "",
        "Generated %s from `%s` (before) and `%s` (after)."
        % (datetime.date.today().isoformat(),
           before.get("run"), after.get("run")),
        "",
    ]
    if metric:
        lines += ["**Metric:** %s" % metric, ""]
    if not same_suite:
        lines += ["> **Warning: the two runs used different suites or "
                  "suite versions. These numbers are NOT comparable.** "
                  "Re-run both on one frozen suite version.", ""]
    lines += [
        "| | Before | After |",
        "|---|---|---|",
        "| Mean score | %.1f%% | %.1f%% |" % (mean_b * 100, mean_a * 100),
        "| Tasks | %d | %d |" % (n_b, n_a),
        "| Total cost | %.4g | %.4g |" % (cost_b, cost_a),
        "| Errors | %d | %d |" % (before.get("errors", 0),
                                  after.get("errors", 0)),
        "",
        "**Change: %+.1f points.**" % delta,
        "",
    ]
    if n_a:
        flip = 100.0 / n_a
        floor = noise_floor if noise_floor is not None else flip
        lines += [
            "With %d tasks, one task flipping moves the mean by %.1f "
            "points. Treat any change smaller than %.1f points as noise, "
            "in either direction." % (n_a, flip, floor),
            "",
        ]
    if improved or regressed:
        lines += ["Tasks that improved: %s." %
                  (", ".join(improved) if improved else "none"),
                  "Tasks that regressed: %s." %
                  (", ".join(regressed) if regressed else "none"), ""]
    if artifacts:
        lines += ["## Installed artifacts", ""]
        lines += ["- %s" % a for a in artifacts]
        lines += ["",
                  "Every artifact above passed the strict-improvement gate "
                  "on the validation split; anything that lost was rolled "
                  "back and is recorded in the run's skill-impact history.",
                  ""]
    lines += [
        "## What to do with this",
        "",
        "- If the change met the threshold your contract set, adopt the "
        "artifacts into daily work and keep light monitoring (re-run the "
        "suite occasionally; redraw it from fresh work when it goes "
        "stale).",
        "- If it did not, the artifacts are rolled back and the baseline "
        "stands — that is the system working, and the record of what was "
        "tried is itself useful.",
        "",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--metric")
    ap.add_argument("--artifacts", nargs="*", default=None)
    ap.add_argument("--noise-floor", type=float, default=None)
    args = ap.parse_args()
    before = json.load(open(args.before, encoding="utf-8"))
    after = json.load(open(args.after, encoding="utf-8"))
    text = generate(before, after, args.metric, args.artifacts,
                    args.noise_floor)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("wrote %s" % args.out)


if __name__ == "__main__":
    main()
