#!/usr/bin/env python3
"""Activity journal — the append-only record of what the coach did.

`workspace/profile/state.json` says where you are. This file says how you
got there: one line per significant act, written the moment it happens,
never edited and never deleted. Weeks later, a new session reads the last
few rows and can say what happened last without asking the user to
remember.

  python3 engine/journal.py append --event stage --step 1-interview \
      --note "Interview finished; profile written."
  python3 engine/journal.py tail -n 10
  python3 engine/journal.py tail -n 5 --json

One row is one JSON object on one line:

  {"utc": "...", "event": "stage", "step": "1-interview",
   "engagement": null, "where": "wikiskills-lab", "note": "..."}

The event vocabulary is small on purpose:

  session      a working session started or ended
  stage        a step or stage completed
  decision     the user chose something (or said "you pick")
  artifact     a file the user gets was written or frozen
  install      something was installed into the user's own world
  deviation    the world stopped matching the contract, and what was done
  inbox        a note arrived from the user's project (return path)
  engagement   an engagement folder was opened, or finished

The journal lives in `workspace/`, which git ignores: it is the user's
record, on their machine only. Secret-shaped text is scrubbed on the way
in with the recorder's own patterns — the fact, never the value.
"""

import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, "recorder"))

from proxy import scrub_text            # noqa: E402

JOURNAL_VERSION = 1
EVENTS = ["session", "stage", "decision", "artifact", "install",
          "deviation", "inbox", "engagement"]


def default_path(workspace=None):
    """The journal file, resolved from THIS file's location.

    The coach may be running from any directory — including the user's own
    project — so the path never depends on the working directory.
    """
    return os.path.join(workspace or os.path.join(REPO, "workspace"),
                        "journal.jsonl")


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def _one_line(text):
    """A row is one line. Newlines and tabs become single spaces."""
    return " ".join(str(text).split())


def append(note, event="session", step=None, engagement=None, where=None,
           path=None, workspace=None):
    """Append one row and return it. Never rewrites what is already there."""
    note = _one_line(scrub_text(_one_line(note)))
    if not note:
        raise ValueError("a journal row needs a note")
    if event not in EVENTS:
        raise ValueError("unknown event %r (use one of: %s)"
                         % (event, ", ".join(EVENTS)))
    row = {
        "v": JOURNAL_VERSION,
        "utc": now_utc(),
        "event": event,
        "step": _one_line(step) if step else None,
        "engagement": _one_line(engagement) if engagement else None,
        "where": _one_line(where) if where else None,
        "note": note,
    }
    path = path or default_path(workspace)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    line = json.dumps(row, ensure_ascii=False) + "\n"
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
        os.fsync(fh.fileno())
    return row


def read(path=None, workspace=None):
    """Every readable row, oldest first. Unreadable lines are skipped."""
    path = path or default_path(workspace)
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def tail(n=10, path=None, workspace=None):
    rows = read(path, workspace)
    return rows[-n:] if n > 0 else rows


def format_row(row):
    parts = [row.get("utc", "?"), row.get("event", "?")]
    for key in ("step", "engagement", "where"):
        if row.get(key):
            parts.append("%s=%s" % (key, row[key]))
    return "%s  %s" % ("  ".join(parts), row.get("note", ""))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("append", help="add one row")
    a.add_argument("--note", required=True, help="one plain sentence")
    a.add_argument("--event", default="session", choices=EVENTS)
    a.add_argument("--step", help="e.g. 3-diagnose")
    a.add_argument("--engagement", help="engagement folder name")
    a.add_argument("--where", help="directory the session ran in")
    a.add_argument("--workspace", help="workspace dir (default: this repo's)")

    t = sub.add_parser("tail", help="show the last rows")
    t.add_argument("-n", type=int, default=10)
    t.add_argument("--json", action="store_true", help="raw rows, one per line")
    t.add_argument("--workspace", help="workspace dir (default: this repo's)")

    args = ap.parse_args()

    if args.cmd == "append":
        try:
            row = append(args.note, event=args.event, step=args.step,
                         engagement=args.engagement, where=args.where,
                         workspace=args.workspace)
        except ValueError as exc:
            print("journal: %s" % exc, file=sys.stderr)
            return 2
        print(format_row(row))
        return 0

    rows = tail(args.n, workspace=args.workspace)
    if not rows:
        print("(no journal yet — nothing has been recorded on this machine)")
        return 0
    for row in rows:
        print(json.dumps(row, ensure_ascii=False) if args.json
              else format_row(row))
    return 0


if __name__ == "__main__":
    sys.exit(main())
