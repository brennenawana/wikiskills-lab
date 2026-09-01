# The return path — start the next improvement from your project folder

After an engagement, the user goes back to daily work in their own project.
The best moment to start the next improvement is the moment a real pain
shows up there — so the coach installs a small skill in the user's own
harness that catches that moment.

**Design rule: the return-path skill is a door, not a copy of the
process.** It knows two things only — where this repository's checkout
lives, and that `START.md` there is the single source of truth. It never
explains the method itself; a copy would drift the first time this
repository updates.

## What invoking it does

1. **Capture the intent while it is concrete.** Ask one question — "What
   do you want to improve?" — and write the answer to
   `<LAB_PATH>/workspace/inbox/` as one file:
   `YYYYMMDD-HHMM-<short-slug>.md`, containing the date, the originating
   project, and the user's words, unedited. No secrets, ever.
2. **Route.** Default: tell the user — "Noted. Open your agent in
   `<LAB_PATH>` and say hello; it will pick this up." If the user says
   "just start here," read `<LAB_PATH>/START.md` and follow it in place,
   using absolute paths for everything under `<LAB_PATH>/workspace/`.

The coach's router checks the inbox on every greeting, so nothing queued
is ever lost.

## Installing

Installed by the coach at the end of step 1 and offered again at step-5
adoption — always with the user's approval, like every write into their
world. Fill `{{LAB_PATH}}` with the absolute path of this repository's
checkout, then use the template for their harness:

| Harness | Template | Where it goes |
|---|---|---|
| Claude Code | `claude-code-skill.md` | a skill in their project's or user's skills directory |
| Cursor / AGENTS.md tools | `rules-snippet.md` | appended to their rules file |
| Custom pipeline / terminal | `improve-alias.sh` | sourced from their shell profile, or dropped in their scripts folder |

Update the installed copy whenever `{{LAB_PATH}}` moves. There is nothing
else in it that can go stale — that is the point.
