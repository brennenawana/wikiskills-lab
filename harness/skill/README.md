# The coach skill — start or resume from anywhere

`SKILL.md` here is the one skill that opens this repository's coach. Install
it once and the user never types "read START.md and follow it" again: they
invoke the skill, and it works out where it was called from, what happened
last, and what to do next.

**Design rule: the skill is a door, not a copy of the process.** It knows
two things — where this checkout lives, and that `START.md` there is the
single source of truth — plus how to read the activity journal. It never
explains the method itself. A copy would drift the first time this
repository updates.

## What invoking it does

1. **Checks the checkout exists.** If it moved, the skill says so and stops,
   rather than improvising the process from memory.
2. **Reads the last activity** — `engine/journal.py tail`, plus
   `workspace/profile/state.json` and `workspace/inbox/` — and opens with a
   plain sentence about where the work stopped, before asking anything.
3. **Routes by where it was called from:**

   | Called from | What happens |
   |---|---|
   | Inside this checkout | Coach mode: read `START.md` and follow it — first visit, resume, or back-for-more |
   | Any other project | Return-path mode: capture "what do you want to improve?" into `workspace/inbox/`, record it in the journal, and offer to either queue it or start right there |

Both modes obey the same rules: write only under `workspace/`, never touch
the user's own repositories or skill files without their approval for that
specific change, journal every stage and decision, and never write a secret
value.

## Installing

```
python3 scripts/install_skill.py            # -> ~/.claude/skills/wikiskills/SKILL.md
python3 scripts/install_skill.py --dry-run  # say what would happen, write nothing
python3 scripts/install_skill.py --dest path/to/project/.claude/skills
python3 scripts/install_skill.py --print    # filled text, for any other harness
```

The installer fills `{{LAB_PATH}}` with the absolute path of **this**
checkout, resolved from its own location, so the installed copy is right by
construction. An existing copy that differs is kept as `SKILL.md.bak`.

Re-run it whenever the checkout moves or is renamed — the path is the only
thing in the installed file that can go stale, which is the point.

## Other harnesses

Harnesses without a skills directory use the same door in their own shape:
see `../return-path/rules-snippet.md` (Cursor and other `AGENTS.md` tools)
and `../return-path/improve-alias.sh` (terminal). Use `--print` above to get
the filled text to paste.
