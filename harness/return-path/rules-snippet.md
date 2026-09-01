# Return-path snippet for rules-file harnesses (Cursor, AGENTS.md tools)

Append this to the project's rules file, with `{{LAB_PATH}}` filled in:

```
When the user wants to improve, measure, or fix how they work with AI
tools (a repeated agent failure, wasted tokens, a skill that needs work):
1. Ask "What do you want to improve?" if not already clear.
2. Write their answer, unedited and with no secret values, to a new file
   {{LAB_PATH}}/workspace/inbox/YYYYMMDD-HHMM-<slug>.md with lines:
   date, from (this project), goal.
3. Say: "Noted. Open your agent in {{LAB_PATH}} and say hello — it will
   pick this up." If they want to start now, read {{LAB_PATH}}/START.md
   and follow it, using absolute paths under {{LAB_PATH}}/workspace/.
Do not explain the improvement process yourself; START.md is the single
source of truth.
```
