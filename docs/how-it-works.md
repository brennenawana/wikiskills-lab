# How it works

One page, for the curious. Nothing here is required reading — the steps
explain themselves as they run.

## The idea

Most teams improve their AI setup by feel: try a prompt, squint at the output,
keep what seems better. That works until it doesn't — you cannot tell whether
a change helped, and yesterday's fix quietly breaks tomorrow's tasks.

This repository applies the method from the WikiSkill paper
(arXiv:2608.27454): treat improvements as **proposals that must prove
themselves**. An optimizer model studies real failure traces and proposes a
change — usually a skill file. The change is tested on a validation set. If
the score strictly improves, it is kept; if not, it is rolled back. Knowledge
about what worked and what failed accumulates in a wiki that persists between
runs. Over iterations, this compounds: the paper shows a small model with
evolved skills beating a much larger bare model, and our own case study
(`benchmarks/spreadsheet/`) reproduces the effect end to end.

## Why measurement comes before improvement

The loop needs three things a normal dev setup does not have: a metric, test
tasks, and a baseline. That is what steps 1–4 build, and why they come first.

- The **interview** maps what a task can touch, so recording covers all of it.
- **Observation** records real work as it happens — measured where the harness
  allows it, self-reported and labeled where it does not — and freezes the
  observed tasks into **capsules**: pinned repository versions plus recorded
  service data. Your real work moves on; the capsules do not. That is what
  makes a before/after comparison honest a month apart.
- **Diagnosis** turns records into a chosen focus — yours if you have one.
- **Measure** turns the focus into a number and takes today's score.

Only then does the loop run, inside budgets and stop rules you approved,
with spending checked before every call.

## What "improvement" means here

Anything text-shaped: skill files, instruction-file changes, tool policies,
context rules, configuration. All of it is diffable, all of it faces the same
gate, and anything that loses is rolled back. You end with a number you
helped define, artifacts installed in your daily work, and records you can
audit.

## Two model tiers

The loop works with the models you already have. Evidence so far (see the
case study and the WikiSkill paper): a fully local setup can evolve useful
skills by itself; adding a stronger model as the optimizer makes discovery
more *reliable* — less run-to-run luck — at extra cost. The interview asks
about your cost reality precisely so this choice, and every budget, is sized
to you.
