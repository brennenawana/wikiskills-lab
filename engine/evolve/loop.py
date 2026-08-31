#!/usr/bin/env python3
"""The evolution loop (WikiSkill Algorithm 1, generalized).

The loop is task-family-agnostic: the executor is injected as a rollout
function, and the two optimizer roles (wiki maintainer, skill proposer) run
over any gateway backend. The rules never change:

- iteration 0 measures validation with the current (initially empty) skills;
- each iteration: train rollout -> maintainer updates the wiki (never rolled
  back) -> proposer proposes ONE atomic change -> the candidate is evaluated
  on validation -> accepted only if the score STRICTLY improves;
- stops: validation = 100%, plateau (consecutive non-accepts), K reached,
  budget (fail closed, checkpointed), crash-rate halt (a broken harness is
  not evidence).

rollout_fn(tasks, skill_section, iteration, trace_dir) -> list of
  {"id": ..., "score": 0..1, "crash": bool}; when trace_dir is not None the
  rollout writes one <task_id>.txt trace file per task into it.
"""

import json
import os
import random
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "gateway"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "budget"))
from gateway import extract_json                    # noqa: E402
from meter import BudgetStop                        # noqa: E402
import wikistore                                    # noqa: E402

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "steps" / "5-improve" \
    / "prompts"

CRASH_RATE_HALT = 0.20
SAMPLE_MAX_FAIL = 5      # maintainer trace sampling, per the paper's App. C
SAMPLE_MAX_PASS = 3
TRACE_CHAR_CAP = 15_000

MAINTAINER_SCHEMA = {
    "type": "object",
    "properties": {
        "create_patterns": {"type": "array", "items": {
            "type": "object",
            "properties": {"name": {"type": "string"},
                           "content": {"type": "string"}},
            "required": ["name", "content"]}},
        "update_patterns": {"type": "array", "items": {
            "type": "object",
            "properties": {"name": {"type": "string"},
                           "edits": {"type": "array"}},
            "required": ["name", "edits"]}},
        "update_index": {"type": "string"},
        "append_log": {"type": "string"},
    },
    "required": ["update_index", "append_log"],
}

PROPOSAL_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string",
                   "enum": ["create", "patch", "no_action"]},
        "name": {"type": "string"},
        "skill_md": {"type": "string"},
        "purpose_md": {"type": "string"},
        "edits": {"type": "array"},
    },
    "required": ["action"],
}

# Ours, not the paper's: how the ReAct proposer's tools map onto a CLI
# session (kept out of the verbatim prompt files).
REACT_TOOL_NOTE = """

## Tool Mapping (this environment)

- `read_file(path)` is available as the **Read** tool. Use paths under the
  workspace root given in the task message (wiki/, skills/, traces/<task_id>.txt).
- `finish(proposal)` is not a tool here: when your investigation is complete,
  output the proposal JSON object as your final answer (the output format is
  schema-enforced). Everything else about the workflow and rules is unchanged."""

PACKET_NOTE = """

## Tool Mapping (this environment)

- You cannot read files in this session. Instead, the message below already
  contains the wiki, the skill-impact history, and sampled execution traces.
- `finish(proposal)` is not a tool here: output the proposal JSON object as
  your final answer, and nothing else. Everything else about the workflow
  and rules is unchanged."""


def _load_prompt(name):
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def _sample_traces(results, trace_dir, seed):
    rng = random.Random(seed)
    fails = [r for r in results if r["score"] < 1.0 and not r.get("crash")]
    passes = [r for r in results if r["score"] >= 1.0]
    rng.shuffle(fails)
    rng.shuffle(passes)
    chosen = fails[:SAMPLE_MAX_FAIL] + passes[:SAMPLE_MAX_PASS]
    parts = []
    for r in chosen:
        p = Path(trace_dir) / ("%s.txt" % r["id"])
        if p.exists():
            parts.append(p.read_text(encoding="utf-8")[:TRACE_CHAR_CAP])
    return "\n\n".join(parts)


def _outcome_summary(results):
    lines = ["task_id | score | verdict"]
    for r in sorted(results, key=lambda x: str(x["id"])):
        verdict = "PASS" if r["score"] >= 1.0 else (
            "CRASH" if r.get("crash") else "FAIL")
        lines.append("%s | %.3f | %s" % (r["id"], r["score"], verdict))
    return "\n".join(lines)


class Roles:
    """Wiki maintainer + skill proposer over a gateway.

    Two proposer modes:
    - "react": a claude-cli session with the Read tool explores the wiki and
      traces itself (the paper's mode).
    - "packet": one call with the wiki and sampled traces included in the
      message — works on ANY backend, including local models with no tools.
    Mode defaults to react for claude-cli optimizers, packet otherwise.
    """

    def __init__(self, gateway, optimizer_cfg, task_desc, meter=None,
                 mode=None, run_tag=None):
        self.gw = gateway
        self.cfg = optimizer_cfg
        self.task_desc = task_desc
        self.meter = meter
        self.mode = mode or ("react" if optimizer_cfg.get("kind") ==
                             "claude-cli" else "packet")
        self.run_tag = run_tag or {}

    def _bill(self, result, role, projection=0.0):
        if self.meter is None:
            return
        cost = result["usd"] if self.meter.unit == "usd" else \
            (result["tokens_in"] + result["tokens_out"])
        self.meter.record(cost, tags=dict(self.run_tag, role=role),
                          model=result.get("model"))

    def maintain(self, run_dir, results, iteration, trace_dir):
        system = _load_prompt("wiki-maintainer.txt")
        traces = _sample_traces(results, trace_dir, seed=iteration)
        user = ("## Current Wiki\n\n%s\n\n"
                "## Execution Traces from Iteration %d\n\n%s\n\n"
                "Analyze the traces against the current wiki and return the "
                "JSON edit object now."
                % (wikistore.wiki_context(run_dir), iteration, traces))
        if self.meter is not None:
            self.meter.precheck(0.0, tags=self.run_tag)
        options = {"json_schema": MAINTAINER_SCHEMA} \
            if self.cfg.get("kind") == "claude-cli" else None
        result = self.gw.call(self.cfg, user, system=system,
                              max_tokens=8192, options=options)
        self._bill(result, "maintainer")
        ops = extract_json(result)
        if not isinstance(ops, dict):
            return ["maintainer returned no parseable JSON; wiki unchanged"]
        return wikistore.apply_maintainer_ops(run_dir, ops, iteration)

    def propose(self, run_dir, results, iteration, trace_dir):
        run_dir = Path(run_dir)
        # .replace, never .format — the verbatim prompt holds literal braces.
        system = _load_prompt("skill-proposer.txt").replace(
            "{task_desc}", self.task_desc)
        index = (run_dir / "wiki" / "index.md").read_text(encoding="utf-8")
        impact = (run_dir / "wiki" / "skill-impact.md").read_text(
            encoding="utf-8")
        head = ("Workspace root: %s\n\n## wiki/index.md\n\n%s\n\n"
                "## wiki/skill-impact.md\n\n%s\n\n"
                "## Training task outcomes (iteration %d)\n\n%s\n\n"
                % (run_dir, index, impact, iteration,
                   _outcome_summary(results)))
        if self.meter is not None:
            self.meter.precheck(0.0, tags=self.run_tag)

        if self.mode == "react":
            system += REACT_TOOL_NOTE
            user = head + ("Begin your investigation. Read pattern pages "
                           "and execution traces as needed, then produce "
                           "your proposal.")
            alias = run_dir / "traces"
            if alias.is_symlink() or alias.exists():
                (alias.unlink() if not alias.is_dir() or alias.is_symlink()
                 else shutil.rmtree(alias))
            try:
                os.symlink(Path(trace_dir).resolve(), alias)
            except OSError:                     # e.g. Windows without perms
                shutil.copytree(trace_dir, alias)
            try:
                result = self.gw.call(
                    self.cfg, user, system=system,
                    options={"tools": "Read", "max_turns": 25,
                             "cwd": str(run_dir),
                             "json_schema": PROPOSAL_SCHEMA})
            finally:
                if alias.is_symlink():
                    alias.unlink()
                elif alias.is_dir():
                    shutil.rmtree(alias)
        else:
            system += PACKET_NOTE
            user = head + ("## wiki (full)\n\n%s\n\n"
                           "## Sampled execution traces\n\n%s\n\n"
                           "Produce your proposal JSON object now."
                           % (wikistore.wiki_context(run_dir),
                              _sample_traces(results, trace_dir,
                                             seed=iteration + 7)))
            result = self.gw.call(self.cfg, user, system=system,
                                  max_tokens=8192)

        self._bill(result, "proposer")
        proposal = extract_json(result)
        if not isinstance(proposal, dict) or "action" not in proposal:
            return {"action": "no_action",
                    "note": "unparseable proposer output"}
        return proposal


def _checkpoint(run_dir, state):
    (Path(run_dir) / "state.json").write_text(json.dumps(state, indent=2),
                                              encoding="utf-8")


def run_evolution(run_dir, train, val, rollout_fn, roles, *, k=8,
                  plateau_stop=3, meter=None, iteration_projection=0.0,
                  run_tag=None):
    """Returns the final state dict; state.json checkpoints every step, so
    the same call resumes an interrupted run."""
    run_dir = Path(run_dir)
    wikistore.init_workspace(run_dir)
    run_tag = run_tag or {}

    state_file = run_dir / "state.json"
    state = (json.loads(state_file.read_text(encoding="utf-8"))
             if state_file.exists() else
             {"iteration_done": 0, "r_best": None, "accepted": [],
              "plateau": 0, "stop_reason": None})

    def rollout(tasks, skills_dir, iteration, trace_name):
        trace_dir = run_dir / "raw" / trace_name if trace_name else None
        if trace_dir:
            trace_dir.mkdir(parents=True, exist_ok=True)
        results = rollout_fn(tasks, wikistore.skills_text(skills_dir),
                             iteration, trace_dir)
        crash_rate = sum(1 for r in results if r.get("crash")) \
            / max(len(results), 1)
        if crash_rate > CRASH_RATE_HALT:
            raise RuntimeError(
                "crash-rate halt: %.0f%% of rollouts crashed — a harness "
                "defect is not evidence; diagnose before continuing"
                % (100 * crash_rate))
        return results

    def mean(results):
        return sum(r["score"] for r in results) / max(len(results), 1)

    def finish(reason):
        state["stop_reason"] = reason
        _checkpoint(run_dir, state)
        (run_dir / "summary.json").write_text(json.dumps(state, indent=2),
                                              encoding="utf-8")
        return state

    try:
        if state["r_best"] is None:
            base = rollout(val, run_dir / "skills", 0, "iter_0_baseline")
            state["r_best"] = mean(base)
            _checkpoint(run_dir, state)

        for it in range(state["iteration_done"] + 1, k + 1):
            if state["r_best"] >= 1.0:
                return finish("early-stop-val-100")
            if state["plateau"] >= plateau_stop:
                return finish("EARLY-PLATEAU")
            if meter is not None:
                meter.precheck(iteration_projection, tags=run_tag)

            trace_name = "iter_%d" % it
            train_results = rollout(train, run_dir / "skills", it,
                                    trace_name)
            trace_dir = run_dir / "raw" / trace_name
            roles.maintain(run_dir, train_results, it, trace_dir)
            prop = roles.propose(run_dir, train_results, it, trace_dir)

            if prop.get("action") == "no_action":
                wikistore.record_skill_impact(
                    run_dir, iteration=it, proposal=prop, val_score="-",
                    best_before=state["r_best"], outcome="NO_ACTION",
                    diff="")
                state["plateau"] += 1
                state["iteration_done"] = it
                _checkpoint(run_dir, state)
                continue

            cand = wikistore.stage_candidate(run_dir)
            changed, diff, notes = wikistore.apply_proposal(cand, prop)
            if not changed:
                wikistore.record_skill_impact(
                    run_dir, iteration=it, proposal=prop, val_score="-",
                    best_before=state["r_best"],
                    outcome="INVALID (%s)" % "; ".join(notes), diff="")
                state["plateau"] += 1
                state["iteration_done"] = it
                _checkpoint(run_dir, state)
                continue

            val_results = rollout(val, cand, it, None)
            score = mean(val_results)
            accepted = score > state["r_best"]     # strictly better, only
            wikistore.record_skill_impact(
                run_dir, iteration=it, proposal=prop,
                val_score="%.4f" % score, best_before=state["r_best"],
                outcome="ACCEPTED" if accepted else "REJECTED", diff=diff)
            if accepted:
                wikistore.promote_candidate(run_dir)
                state["r_best"] = score
                state["accepted"].append(
                    {"iteration": it, "action": prop.get("action"),
                     "name": prop.get("name"), "val": score})
                state["plateau"] = 0
            else:
                state["plateau"] += 1
            state["iteration_done"] = it
            _checkpoint(run_dir, state)

        return finish("completed-K")

    except BudgetStop as exc:
        return finish("STOPPED-BUDGET: %s" % exc)
    except RuntimeError as exc:
        return finish(str(exc))
