# Step 2 — Observe

**Status: not yet available in this version.** Tell the user so, plainly, and
stop here. Their step-1 profile is safe in `workspace/profile/` and will be
used the moment this step lands.

What this step will do: record one or more of the user's real tasks, done the
normal way — every file read, every service call, every token spent, every
human intervention — into durable ledger files in `workspace/ledgers/`.
Recording uses the strongest available method for their harness (see
`harness/`), and every record is labeled with how it was captured: measured,
or self-reported. The observed task is also frozen into a repeatable test
capsule in `workspace/capsules/`, so later measurements can replay it even
after the real work has moved on.
