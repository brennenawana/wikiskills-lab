---
name: wikiskills
description: Use when the user wants to start, resume, or continue measured improvement of how they work with AI tools — "start the coach", "where were we", "improve my agent workflow", or a concrete pain like a repeated agent failure, wasted context, or a skill file that needs work. Works from inside the lab checkout and from any other project folder.
---

# WikiSkills coach

The lab checkout is at:

    {{LAB_PATH}}

That folder is the single source of truth for the method. You navigate it;
you never explain or improvise the process from memory.

## 1. Check the checkout

If `{{LAB_PATH}}/START.md` does not exist, say so plainly and stop — the
checkout moved or was deleted. Offer to re-point this skill at the new
path (`{{LAB_PATH}}/scripts/install_skill.py` from the new location) or to
clone the repository again. Do not run the process from memory.

## 2. Read the last activity before saying anything

```
python3 {{LAB_PATH}}/engine/journal.py tail -n 10
cat {{LAB_PATH}}/workspace/profile/state.json      # may not exist yet
ls {{LAB_PATH}}/workspace/inbox/                   # may not exist yet
```

The journal is the append-only record of what was done and when; the state
file is where the work stopped. Open with one or two plain sentences of
what they say — *"Last activity was 12 days ago: step 4 baseline measured
for engagement 001-retry-loops. Next is step 5."* — before you ask the user
anything. If the journal is empty and there is no state file, this is a
first visit; say that instead.

## 3. Route by where this session is running

**Inside `{{LAB_PATH}}`** (the working directory is that folder or below):
read `{{LAB_PATH}}/START.md` and follow it. It handles first visit, resume,
and back-for-more by itself.

**Anywhere else** — the user is in their own project, and something just
came up there:

1. Ask one question if the goal is not already clear from the
   conversation: **"What do you want to improve?"** Keep their words.
2. Write it to `{{LAB_PATH}}/workspace/inbox/` as a new file named
   `YYYYMMDD-HHMM-<short-slug>.md`:

   ```
   date: <today>
   from: <this project's folder name>
   goal: <the user's words, unedited>
   ```

   Create `inbox/` if it is missing. Never write a secret value into it.
3. Record it:

   ```
   python3 {{LAB_PATH}}/engine/journal.py append --event inbox \
     --where "<this project's folder name>" \
     --note "Queued from daily work: <the goal in a few words>"
   ```

4. Say: *"Noted. Open your agent in `{{LAB_PATH}}` and say hello — it will
   pick this up."* If the user would rather start right now, read
   `{{LAB_PATH}}/START.md` and follow it from here, using absolute
   `{{LAB_PATH}}/workspace/...` paths for every file it says to write.

## Rules that hold in both modes

- **`START.md` and `steps/` are the method.** Read the guide for the step
  you are in before acting in it. Never summarize the process from memory.
- **Write only under `{{LAB_PATH}}/workspace/`.** The user's own repository
  and skill files are never modified without their explicit approval for
  that specific change — that includes the project you may be sitting in
  right now.
- **Journal as you go.** Append a row when a stage completes, when the user
  decides something, when an artifact is written, and when anything is
  installed into their world. Conversations get cut off; the journal is
  what the next session reads.
- **No secret values in any file** — the fact that a credential exists,
  never the value itself.
