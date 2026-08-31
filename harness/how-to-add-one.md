# Adding a harness

Each file in this folder answers three questions about one harness, in this
order and in plain language:

1. **Recognize it.** What signals identify this harness — instruction files
   it honors, CLIs on PATH, config files, how the user describes it.
2. **What observation will look like.** For each kind of activity (model
   calls, file access, commands, outside services): can it be **measured**
   (harness logs, hooks, or traffic through a configurable endpoint), or only
   **self-reported** (the working agent writing its own ledger)? Be honest;
   the labels follow the data through every later step.
3. **Notes for later steps.** Where improvement artifacts install in this
   harness (which files, which settings).

Keep it short — under 40 lines. Prefer "measured" paths through configurable
endpoints over clever workarounds; they age better. Send a pull request.
