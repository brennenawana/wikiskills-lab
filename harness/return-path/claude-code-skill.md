---
name: improve-my-ai-workflow
description: Use when the user wants to improve, measure, or fix how they work with AI tools — a repeated agent failure, wasted context or tokens, a skill file that needs work, or "this could work better". Captures the goal and routes to their improvement workspace.
---

# Improve my AI workflow

The user's measured-improvement workspace lives at:

    {{LAB_PATH}}

## What to do

1. Ask one question, if the goal is not already clear from the
   conversation: **"What do you want to improve?"** Keep their answer in
   their own words.
2. Write it to `{{LAB_PATH}}/workspace/inbox/` as a new file named
   `YYYYMMDD-HHMM-<short-slug>.md`:

   ```
   date: <today>
   from: <this project's folder name>
   goal: <the user's words, unedited>
   ```

   Never include secret values. Create the `inbox/` folder if missing.
3. Tell the user: "Noted. Open your agent in `{{LAB_PATH}}` and say hello
   — it will pick this up and suggest next steps."
4. If the user says to start right away, read `{{LAB_PATH}}/START.md` and
   follow it from here, using absolute `{{LAB_PATH}}/workspace/...` paths
   for every file it says to write.

Do not explain or improvise the improvement process yourself — START.md
is the single source of truth for it.
