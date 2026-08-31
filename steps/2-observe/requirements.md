# The Observability Checklist

Recording setups differ across projects and operating systems, and that is
fine — this repository does not require its own tools. What it requires is
that **whatever records the session meets this checklist**. The checklist is
the standard; the tools are replaceable.

One principle above all: **trust the probe, not the brochure.** No
requirement counts as met because a tool's documentation says so, because
the vendor is famous, or because it worked somewhere else once. It counts as
met when a miniature test (`probes.md`) demonstrated it **on this machine**.

## The requirements

An observed session produces one or more **streams** (model calls, agent
actions, outside-service traffic). Each stream a plan claims as *measured*
must meet every MUST below.

| # | Requirement | Level |
|---|---|---|
| O1 | **Complete capture.** Every event in the stream produces exactly one ledger row. No sampling, no "only the important ones", no silent drops under load. | MUST |
| O2 | **Cost visibility** (model-call streams). Token counts per call, with every usage entry in a response summed — not just the first. If a transport hides usage (some streaming modes do), the plan must switch it on; otherwise the stream is not "measured". | MUST |
| O3 | **No behavior change.** Observation must not alter the observed work: responses byte-identical, no prompt edits, no blocking, no failure mode where the recorder breaks the agent. | MUST |
| O4 | **Durable, append-only ledgers.** Plain files on disk, outside any conversation context, appended and never rewritten, surviving a crash of the observed session. | MUST |
| O5 | **Timestamped and ordered.** Every row carries a UTC timestamp; row order matches event order. | MUST |
| O6 | **No secrets on disk.** Auth headers, tokens, keys, passwords are scrubbed at write time. A ledger must be safe to read aloud in a meeting. | MUST |
| O7 | **Evidence labeling.** Every stream is labeled `measured` or `self-reported` in the session manifest. Self-reported data is allowed — unlabeled data is not. | MUST |
| O8 | **Replay raw material.** The recorder can keep full (scrubbed) request/response bodies, so observed service data can later become frozen test fixtures. | SHOULD |
| O9 | **Probe-verified.** Every MUST above has been demonstrated by a probe on this machine, and a calibration canary ran end to end, before the real session. | MUST |
| O10 | **Blast-radius coverage.** Every repository and service in the step-1 blast radius is either covered by a stream or listed as an explicit, user-acknowledged gap. Silent gaps fail the whole plan. | MUST |

## The acceptance rule

When the user proposes their own tooling ("I have tool A and program B"),
do not argue about the tools — evaluate them:

1. Build a **coverage table**: streams down the side, O1–O10 across the top.
2. Fill each cell with `yes`, `no`, or `unknown`, based on what the tool can
   actually show, not what it claims.
3. Resolve every `unknown` with a probe (`probes.md`). A tool that offers no
   way to probe it — no ledger you can read, no test you can run — is
   resolved to `no`.
4. Verdict:
   - **ACCEPT** — all MUSTs pass by probe.
   - **ACCEPT WITH LABELED GAPS** — MUSTs pass; some SHOULD is unmet or some
     stream is self-reported; the user approves each gap, and each gap is
     written into the session manifest and follows the data into every
     later finding.
   - **REJECT** — any MUST fails and cannot be fixed. Say it plainly and
     kindly: *"Tool A cannot show us its rows for the calls we just made,
     so we cannot treat its output as measurement. Here is what I suggest
     instead."* Then offer the nearest default from `harness/` — the
     recording proxy, the hooks pack, or a labeled self-report plan.

Never soften a REJECT into silence. A finding built on unverified recording
is worse than no finding: it looks like knowledge.

## The rule applies to our own tools too

The proxy and hooks pack in `engine/recorder/` get no exemption. They are
accepted on a given machine only after `probe.py proxy` and `probe.py hook`
pass there — same checklist, same probes, same rejection if they fail.
