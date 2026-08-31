#!/usr/bin/env python3
"""Release gates — run before any push, and before the repo goes public.

  python3 scripts/release_gate.py           # all gates
  python3 scripts/release_gate.py --quick   # skip probes/selftests

Gates:
1. Vocabulary: no tracked file contains a banned term (private project
   names and other words that must never appear in this repository).
2. Redistribution: nothing authored by the benchmark upstream has EVER
   been committed — checked across all git history, not just the tip.
3. Tests: engine selftests and all recorder probes pass on this machine
   (skipped with --quick).

Exit 0 = release-ready. Anything else: fix it first.
"""

import argparse
import fnmatch
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SELF = os.path.relpath(os.path.abspath(__file__), REPO)

# Terms are assembled at run time so this file never matches its own scan.
BANNED_TERMS = [
    "F" + "IS",                 # case-sensitive (see scan below)
    "SE" + "-1",
    "wholesal",
    "millw" + "ork",
    "playb" + "ook",
    "EVIDENCE" + "_MAP",
    "adaptive" + "-ai-lab",
    "batt" + "ery",
    "deli" + "ght",
]
CASE_SENSITIVE = {"F" + "IS", "SE" + "-1"}  # short terms; lowercase would
                                            # false-positive ordinary words

# Files the benchmark upstream authored — must never appear in history.
FORBIDDEN_HISTORY = ["*.xlsx", "*.tar.gz", "evaluation.py",
                     "open_spreadsheet.py", "dataset.json",
                     "benchmarks/spreadsheet/data/*"]

# Maintainer-local paths (dev notes about this repo) — gitignored, and this
# gate also refuses them if force-added by accident.
PRIVATE_PATHS = ["local/*", "NOTES.md", "TODO.md"]

FAILURES = []


def fail(msg):
    FAILURES.append(msg)
    print("  [FAIL] %s" % msg)


def ok(msg):
    print("  [ok]   %s" % msg)


def git(*args):
    return subprocess.run(["git", "-C", REPO, *args], capture_output=True,
                          text=True, check=True).stdout


def gate_vocabulary():
    print("Gate 1 — vocabulary:")
    files = [f for f in git("ls-files").splitlines()
             if f and f != SELF.replace(os.sep, "/")]
    hits = 0
    for path in files:
        full = os.path.join(REPO, path)
        try:
            text = open(full, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        lowered = text.lower()
        for term in BANNED_TERMS:
            found = (term in text) if term in CASE_SENSITIVE \
                else (term.lower() in lowered)
            if found:
                fail("%s contains banned term %r" % (path, term))
                hits += 1
    private = [f for f in files
               if any(fnmatch.fnmatch(f, pat) for pat in PRIVATE_PATHS)]
    for p in private:
        fail("maintainer-local path is tracked: %s (dev notes never ship)"
             % p)
    if not hits and not private:
        ok("%d tracked files clean" % len(files))


def gate_history():
    print("Gate 2 — redistribution (all git history):")
    seen = set()
    for line in git("log", "--all", "--pretty=format:",
                    "--name-only").splitlines():
        line = line.strip()
        if line:
            seen.add(line)
    bad = sorted(
        p for p in seen
        if any(fnmatch.fnmatch(p, pat)
               or fnmatch.fnmatch(os.path.basename(p), pat)
               for pat in FORBIDDEN_HISTORY))
    if bad:
        for p in bad:
            fail("history contains upstream-shaped file: %s" % p)
    else:
        ok("%d paths ever tracked; none upstream-authored" % len(seen))


def gate_tests():
    print("Gate 3 — selftests and probes:")
    jobs = [("engine selftests", [sys.executable, "engine/selftest.py"]),
            ("proxy probe", [sys.executable, "engine/recorder/probe.py",
                             "proxy"]),
            ("hook probe", [sys.executable, "engine/recorder/probe.py",
                            "hook"]),
            ("replay probe", [sys.executable, "engine/recorder/probe.py",
                              "replay"])]
    for name, cmd in jobs:
        proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
        if proc.returncode == 0:
            ok(name)
        else:
            fail("%s failed:\n%s" % (name, proc.stdout[-800:]))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quick", action="store_true",
                    help="skip gate 3 (tests)")
    args = ap.parse_args()
    gate_vocabulary()
    gate_history()
    if not args.quick:
        gate_tests()
    print()
    if FAILURES:
        print("RELEASE GATE FAILED: %d problem(s). Do not push; do not "
              "flip the repo public." % len(FAILURES))
        sys.exit(1)
    print("RELEASE GATE PASSED.")


if __name__ == "__main__":
    main()
