#!/usr/bin/env python3
"""Task capsules — frozen, replayable copies of real work.

Real work moves on (PRs merge, boards change) while evaluations must
replay. A capsule freezes everything one task needs:

- capsule.json      the manifest: task, repo pins, fixture hashes, env
- fixtures/         recorded third-party exchanges (served hermetically by
                    the proxy's replay mode; misses fail closed)
- files/            any input files copied verbatim

Rollouts run in disposable checkouts made from the pinned commits — never
in the developer's live working tree. Capsules live in workspace/ (local
only, git-ignored): the tool is public; captured worlds never are.

  python3 capsule.py create --dir workspace/capsules/t-001 \
      --task "PROJ-123: fix the retry loop" \
      --repo ../their-project [--repo ../their-lib] \
      [--fixtures workspace/ledgers/capture] [--files input.xlsx ...]
  python3 capsule.py verify --dir workspace/capsules/t-001
  python3 capsule.py checkout --dir workspace/capsules/t-001 --dest /tmp/x

Standard library only.
"""

import argparse
import datetime
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(
        timespec="seconds")


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(repo, *args):
    proc = subprocess.run(["git", "-C", repo, *args], capture_output=True,
                          text=True)
    if proc.returncode != 0:
        raise SystemExit("git %s failed in %s: %s"
                         % (" ".join(args), repo, proc.stderr.strip()))
    return proc.stdout.strip()


def create(capsule_dir, task, repos, fixtures_dir=None, files=None):
    os.makedirs(os.path.join(capsule_dir, "fixtures"), exist_ok=True)
    os.makedirs(os.path.join(capsule_dir, "files"), exist_ok=True)

    repo_pins = []
    for repo in repos:
        commit = _git(repo, "rev-parse", "HEAD")
        dirty = bool(_git(repo, "status", "--porcelain"))
        repo_pins.append({"path": os.path.abspath(repo), "commit": commit,
                          "dirty_at_freeze": dirty})
        if dirty:
            print("warning: %s has uncommitted changes; the pin records "
                  "HEAD, not those changes" % repo, file=sys.stderr)

    fixture_hashes = {}
    if fixtures_dir:
        for fn in sorted(os.listdir(fixtures_dir)):
            if fn.endswith(".json"):
                src = os.path.join(fixtures_dir, fn)
                dst = os.path.join(capsule_dir, "fixtures", fn)
                shutil.copy2(src, dst)
                fixture_hashes[fn] = _sha256(dst)

    file_hashes = {}
    for f in files or []:
        dst = os.path.join(capsule_dir, "files", os.path.basename(f))
        shutil.copy2(f, dst)
        file_hashes[os.path.basename(f)] = _sha256(dst)

    manifest = {
        "v": 1, "created": _now(), "task": task,
        "repos": repo_pins,
        "fixtures": fixture_hashes,
        "files": file_hashes,
        "environment": {"os": platform.platform(),
                        "python": platform.python_version()},
        "replay": "serve fixtures/ with: python3 engine/recorder/proxy.py "
                  "--replay <this dir>/fixtures --ledger <run>/replay.jsonl",
    }
    path = os.path.join(capsule_dir, "capsule.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
    return manifest


def verify(capsule_dir):
    """Check every recorded hash. Returns (ok, problems)."""
    problems = []
    path = os.path.join(capsule_dir, "capsule.json")
    if not os.path.exists(path):
        return False, ["capsule.json missing"]
    manifest = json.load(open(path, encoding="utf-8"))
    for sub, hashes in (("fixtures", manifest.get("fixtures", {})),
                        ("files", manifest.get("files", {}))):
        for fn, expected in hashes.items():
            p = os.path.join(capsule_dir, sub, fn)
            if not os.path.exists(p):
                problems.append("%s/%s missing" % (sub, fn))
            elif _sha256(p) != expected:
                problems.append("%s/%s hash mismatch (frozen content "
                                "changed)" % (sub, fn))
    return not problems, problems


def checkout(capsule_dir, dest):
    """Disposable checkouts of every pinned repo, never the live tree."""
    manifest = json.load(open(os.path.join(capsule_dir, "capsule.json"),
                              encoding="utf-8"))
    os.makedirs(dest, exist_ok=True)
    out = []
    for pin in manifest["repos"]:
        name = os.path.basename(pin["path"].rstrip("/"))
        target = os.path.join(dest, name)
        subprocess.run(["git", "clone", "--quiet", pin["path"], target],
                       check=True)
        _git(target, "checkout", "--quiet", pin["commit"])
        out.append(target)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=["create", "verify", "checkout"])
    ap.add_argument("--dir", required=True, help="capsule directory")
    ap.add_argument("--task", help="one-line task description (create)")
    ap.add_argument("--repo", action="append", default=[],
                    help="blast-radius repo path; repeatable (create)")
    ap.add_argument("--fixtures", help="capture dir to freeze (create)")
    ap.add_argument("--files", nargs="*", default=[],
                    help="input files to copy in (create)")
    ap.add_argument("--dest", help="checkout destination")
    args = ap.parse_args()

    if args.mode == "create":
        if not args.task:
            ap.error("--task is required for create")
        m = create(args.dir, args.task, args.repo, args.fixtures, args.files)
        print(json.dumps(m, indent=1))
    elif args.mode == "verify":
        ok, problems = verify(args.dir)
        print("OK" if ok else "FAILED:\n" + "\n".join(problems))
        sys.exit(0 if ok else 1)
    else:
        if not args.dest:
            ap.error("--dest is required for checkout")
        for p in checkout(args.dir, args.dest):
            print(p)


if __name__ == "__main__":
    main()
