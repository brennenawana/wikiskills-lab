#!/usr/bin/env python3
"""Install the coach skill so it can be invoked from anywhere.

The skill is a door, not a copy of the method: it holds the path to this
checkout and nothing else. This script fills that path in — resolved from
where this file actually lives, so it is right by construction — and writes
the skill where the harness looks for it.

  python3 scripts/install_skill.py                 # ~/.claude/skills/wikiskills/
  python3 scripts/install_skill.py --dry-run       # print it, write nothing
  python3 scripts/install_skill.py --dest DIR      # a project's skills dir
  python3 scripts/install_skill.py --print         # to stdout, for other harnesses

Re-run it after moving or renaming the checkout; that is the only thing in
the installed file that can go stale.
"""

import argparse
import os
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(REPO, "harness", "skill", "SKILL.md")
SKILL_NAME = "wikiskills"
DEFAULT_DEST = os.path.join(os.path.expanduser("~"), ".claude", "skills")


def render():
    with open(TEMPLATE, encoding="utf-8") as fh:
        text = fh.read()
    if "{{LAB_PATH}}" not in text:
        raise SystemExit("template has no {{LAB_PATH}} placeholder: %s"
                         % TEMPLATE)
    return text.replace("{{LAB_PATH}}", REPO)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dest", default=DEFAULT_DEST,
                    help="skills directory (default: %s)" % DEFAULT_DEST)
    ap.add_argument("--name", default=SKILL_NAME,
                    help="skill folder name (default: %s)" % SKILL_NAME)
    ap.add_argument("--dry-run", action="store_true",
                    help="say what would happen; write nothing")
    ap.add_argument("--print", dest="to_stdout", action="store_true",
                    help="print the filled skill and exit")
    args = ap.parse_args()

    if not os.path.exists(TEMPLATE):
        raise SystemExit("missing template: %s" % TEMPLATE)
    text = render()

    if args.to_stdout:
        sys.stdout.write(text)
        return 0

    target_dir = os.path.join(os.path.expanduser(args.dest), args.name)
    target = os.path.join(target_dir, "SKILL.md")

    if args.dry_run:
        print("would write %s" % target)
        print("  lab path:  %s" % REPO)
        if os.path.exists(target):
            same = open(target, encoding="utf-8").read() == text
            print("  existing:  %s" % ("identical" if same
                                       else "differs (would be replaced, "
                                            "old copy kept as SKILL.md.bak)"))
        return 0

    os.makedirs(target_dir, exist_ok=True)
    if os.path.exists(target) and \
            open(target, encoding="utf-8").read() != text:
        shutil.copyfile(target, target + ".bak")
        print("kept previous copy: %s.bak" % target)
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(text)

    print("installed %s" % target)
    print("lab path:  %s" % REPO)
    print("Invoke it from any project with /%s (restart the harness if it "
          "does not appear yet)." % args.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
