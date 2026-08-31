#!/usr/bin/env python3
"""Fail-closed budget meter and test-look ledger.

Two rules, learned the hard way:

1. Check the cap BEFORE spending, never after. If the check cannot run, do
   not spend (fail closed).
2. The append-only ledger is the truth. Totals are recomputed from it, never
   trusted from memory.

Costs are floats in whatever unit the caps file declares ("usd", "tokens",
"gpu-minutes", ...). The meter does not care which — it only compares.
Standard library only; file locking works on POSIX and Windows.
"""

import datetime
import json
import os


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(
        timespec="milliseconds")


class _FileLock:
    """Cross-platform exclusive lock on a sidecar .lock file."""

    def __init__(self, path):
        self.path = path + ".lock"
        self.fh = None

    def __enter__(self):
        self.fh = open(self.path, "a+b")
        try:
            import fcntl
            fcntl.flock(self.fh, fcntl.LOCK_EX)
        except ImportError:                       # Windows
            import msvcrt
            self.fh.seek(0)
            msvcrt.locking(self.fh.fileno(), msvcrt.LK_LOCK, 1)
        return self

    def __exit__(self, *exc):
        try:
            try:
                import fcntl
                fcntl.flock(self.fh, fcntl.LOCK_UN)
            except ImportError:
                import msvcrt
                self.fh.seek(0)
                msvcrt.locking(self.fh.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            self.fh.close()


class BudgetStop(Exception):
    """Raised BEFORE a call that would breach a cap. Carries the consequence."""

    def __init__(self, scope, limit, spent, estimate, consequence):
        self.scope, self.limit = scope, limit
        self.spent, self.estimate = spent, estimate
        self.consequence = consequence
        super().__init__(
            "budget stop on scope '%s': spent %.4f + estimate %.4f would "
            "pass the cap %.4f. Consequence: %s"
            % (scope, spent, estimate, limit, consequence))


class Meter:
    """caps: {"unit": "usd", "caps": [
         {"scope": "total", "limit": 5.0, "consequence": "..."},
         {"scope": "run:baseline", "limit": 2.0, "consequence": "..."}]}

    A row's scopes come from its tags: every row counts toward "total";
    a row with {"run": "baseline"} also counts toward "run:baseline".
    """

    def __init__(self, ledger_path, caps):
        self.ledger_path = ledger_path
        self.unit = caps.get("unit", "usd")
        self.caps = caps.get("caps", [])
        os.makedirs(os.path.dirname(os.path.abspath(ledger_path)),
                    exist_ok=True)

    def _rows(self):
        if not os.path.exists(self.ledger_path):
            return []
        rows = []
        with open(self.ledger_path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    rows.append(json.loads(line))
        return rows

    def spent(self, scope="total"):
        total = 0.0
        for row in self._rows():
            if scope == "total":
                total += row.get("cost", 0.0)
            elif ":" in scope:
                key, val = scope.split(":", 1)
                if str(row.get(key)) == val:
                    total += row.get("cost", 0.0)
        return total

    def precheck(self, estimate, tags=None):
        """Raise BudgetStop if this spend could pass any cap. Call before
        EVERY spend. A cap that cannot be evaluated fails closed."""
        tags = tags or {}
        with _FileLock(self.ledger_path):
            for cap in self.caps:
                scope = cap["scope"]
                applies = scope == "total"
                if ":" in scope:
                    key, val = scope.split(":", 1)
                    applies = str(tags.get(key)) == val
                if not applies:
                    continue
                already = self.spent(scope)
                if already + float(estimate) > float(cap["limit"]):
                    raise BudgetStop(scope, float(cap["limit"]), already,
                                     float(estimate),
                                     cap.get("consequence",
                                             "halt; ask the owner"))

    def record(self, cost, tags=None, **meta):
        row = {"v": 1, "ts": _now(), "cost": float(cost), "unit": self.unit}
        row.update(tags or {})
        row.update(meta)
        with _FileLock(self.ledger_path):
            with open(self.ledger_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        return row


class LookLedger:
    """One look at held-out results per planned key, spent before the run.

    - plan(key): declare a look before any of them is taken.
    - spend(key, results_path): append the spend row. REFUSED if the key was
      already spent AND a results file exists (someone saw numbers).
      Allowed again if spent but no results exist — an interrupted run
      continues as the SAME look, because nobody saw anything.
    """

    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    def _rows(self):
        if not os.path.exists(self.path):
            return []
        with open(self.path, encoding="utf-8") as fh:
            return [json.loads(l) for l in fh if l.strip()]

    def plan(self, key, note=None):
        with _FileLock(self.path):
            if any(r.get("planned") == key for r in self._rows()):
                return
            with open(self.path, "a", encoding="utf-8") as fh:
                row = {"v": 1, "ts": _now(), "planned": key}
                if note:
                    row["note"] = note
                fh.write(json.dumps(row) + "\n")

    def spend(self, key, results_path):
        with _FileLock(self.path):
            rows = self._rows()
            if not any(r.get("planned") == key for r in rows):
                raise RuntimeError(
                    "look '%s' was never planned; unplanned looks at "
                    "held-out results are refused" % key)
            already = any(r.get("spent") == key for r in rows)
            if already and os.path.exists(results_path):
                raise RuntimeError(
                    "look '%s' is already spent and results exist; a second "
                    "look would invalidate the comparison" % key)
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(
                    {"v": 1, "ts": _now(), "spent": key,
                     "continuation": already}) + "\n")
