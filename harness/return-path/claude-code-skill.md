# Claude Code — use the coach skill

There is one Claude Code skill, and it lives in `../skill/SKILL.md`. It is
the same door in both directions: invoked inside this checkout it opens the
coach, invoked from the user's own project it captures the goal into
`workspace/inbox/` and routes.

```
python3 scripts/install_skill.py                             # user-level
python3 scripts/install_skill.py --dest <project>/.claude/skills   # project-level
```

See `../skill/README.md`. This file used to hold a second, project-scoped
copy of the same instructions; one door cannot drift, two can.
