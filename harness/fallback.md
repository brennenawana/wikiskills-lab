# Harness: anything else

No match in this folder? Observation still works, but it is weaker — say so
to the user in plain words.

## What observation will look like (step 2)

- If the model endpoint is configurable anywhere in their setup, use the
  recording proxy for **measured** model-call ledgers.
- Otherwise everything is **self-reported**: the harness's instruction file
  (whatever it honors) tells the working agent to append one line per
  significant action — file touched, command run, service called — to a
  ledger file. The working agent grading its own homework is better than
  nothing, but every finding built on it must carry the "self-reported"
  label.

## Help us do better

If you know this harness well, `how-to-add-one.md` explains how to
contribute a proper entry for it.
