#!/usr/bin/env python3
"""The three storage layers of the evolution loop (after WikiSkill,
arXiv:2608.27454 — see CREDITS.md):

- raw/       immutable execution traces, never edited
- wiki/      persistent knowledge (index, log, skill-impact, patterns/),
             updated every iteration and NEVER rolled back
- skills/    the gated layer: changes land here only after passing the
             strict-improvement gate

Standard library only.
"""

import difflib
import re
import shutil
from pathlib import Path

INDEX_SEED = "# Pattern Index\n\n(no patterns yet)\n"
LOG_SEED = "# Evolution Log\n"
IMPACT_SEED = "# Skill Impact History\n"


def init_workspace(run_dir):
    run_dir = Path(run_dir)
    (run_dir / "wiki" / "patterns").mkdir(parents=True, exist_ok=True)
    (run_dir / "skills").mkdir(exist_ok=True)
    (run_dir / "raw").mkdir(exist_ok=True)
    for name, seed in [("index.md", INDEX_SEED), ("log.md", LOG_SEED),
                       ("skill-impact.md", IMPACT_SEED)]:
        p = run_dir / "wiki" / name
        if not p.exists():
            p.write_text(seed, encoding="utf-8")


def wiki_context(run_dir):
    run_dir = Path(run_dir)
    parts = []
    for rel in ["wiki/index.md", "wiki/log.md"]:
        parts.append("=== %s ===\n%s"
                     % (rel, (run_dir / rel).read_text(encoding="utf-8")))
    # Human hints: the run's owner may leave notes for the optimizer roles.
    notes = run_dir / "wiki" / "owner-notes.md"
    if notes.exists():
        parts.append("=== wiki/owner-notes.md (written by the human owner "
                     "— treat as strong hints) ===\n%s"
                     % notes.read_text(encoding="utf-8"))
    for p in sorted((run_dir / "wiki" / "patterns").glob("*.md")):
        parts.append("=== wiki/patterns/%s ===\n%s"
                     % (p.name, p.read_text(encoding="utf-8")))
    return "\n\n".join(parts)


def _safe_name(name, suffix=".md"):
    name = Path(name).name
    name = re.sub(r"[^A-Za-z0-9._-]", "-", name)
    if suffix and not name.endswith(suffix):
        name += suffix
    return name


def apply_patch_ops(text, edits):
    """The paper's three patch operations. Unknown ops and missing targets
    are reported, never guessed."""
    notes = []
    for e in edits or []:
        op = e.get("op")
        content = e.get("content", "")
        target = e.get("target", "")
        if op == "append":
            text = text.rstrip("\n") + "\n" + content + "\n"
        elif op == "replace":
            if target and target in text:
                text = text.replace(target, content, 1)
            else:
                notes.append("replace target not found: %r" % target[:60])
        elif op == "insert_after":
            if target and target in text:
                i = text.index(target) + len(target)
                text = text[:i] + "\n" + content + text[i:]
            else:
                notes.append("insert_after target not found: %r"
                             % target[:60])
        else:
            notes.append("unknown op: %r" % op)
    return text, notes


def apply_maintainer_ops(run_dir, ops, iteration):
    """Apply the maintainer's JSON edit object to wiki/. Never rolls back."""
    run_dir = Path(run_dir)
    notes = []
    pat_dir = run_dir / "wiki" / "patterns"
    for item in ops.get("create_patterns") or []:
        name = _safe_name(item.get("name", "unnamed"))
        (pat_dir / name).write_text(item.get("content", ""),
                                    encoding="utf-8")
    for item in ops.get("update_patterns") or []:
        name = _safe_name(item.get("name", ""))
        p = pat_dir / name
        if not p.exists():
            notes.append("update target missing: %s" % name)
            continue
        text, n = apply_patch_ops(p.read_text(encoding="utf-8"),
                                  item.get("edits"))
        p.write_text(text, encoding="utf-8")
        notes.extend(n)
    if isinstance(ops.get("update_index"), str):
        (run_dir / "wiki" / "index.md").write_text(ops["update_index"],
                                                   encoding="utf-8")
    if isinstance(ops.get("append_log"), str):
        with (run_dir / "wiki" / "log.md").open("a", encoding="utf-8") as f:
            f.write("\n## [iter %d] %s\n" % (iteration, ops["append_log"]))
    return notes


# --- skills layer ----------------------------------------------------------

def skills_text(skills_dir):
    """The skill section injected into the executor's system prompt: every
    accepted SKILL.md, in full."""
    skills_dir = Path(skills_dir)
    parts = []
    if skills_dir.is_dir():
        for d in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
            md = d / "SKILL.md"
            if md.exists():
                parts.append("### Skill: %s\n\n%s"
                             % (d.name, md.read_text(encoding="utf-8")))
    if not parts:
        return ""
    return "## Available Skills\n\n" + "\n\n".join(parts)


def _tree_text(skills_dir):
    out = {}
    for d in sorted(p for p in Path(skills_dir).iterdir() if p.is_dir()):
        for f in sorted(d.glob("*.md")):
            out["%s/%s" % (d.name, f.name)] = f.read_text(encoding="utf-8")
    return out


def apply_proposal(skills_dir, proposal):
    """Apply a create/patch proposal to a skills dir. Returns
    (changed, unified_diff, notes)."""
    skills_dir = Path(skills_dir)
    before = _tree_text(skills_dir)
    notes = []
    action = proposal.get("action")
    if action == "create":
        name = _safe_name(proposal.get("name", "unnamed_skill"), suffix="")
        d = skills_dir / name
        d.mkdir(exist_ok=True)
        (d / "SKILL.md").write_text(proposal.get("skill_md", ""),
                                    encoding="utf-8")
        (d / "PURPOSE.md").write_text(proposal.get("purpose_md", ""),
                                      encoding="utf-8")
    elif action == "patch":
        name = _safe_name(proposal.get("name", ""), suffix="")
        md = skills_dir / name / "SKILL.md"
        if not md.exists():
            return False, "", ["patch target skill missing: %s" % name]
        text, n = apply_patch_ops(md.read_text(encoding="utf-8"),
                                  proposal.get("edits"))
        md.write_text(text, encoding="utf-8")
        notes.extend(n)
    else:
        return False, "", ["no-op action: %r" % action]

    after = _tree_text(skills_dir)
    diff_parts = []
    for key in sorted(set(before) | set(after)):
        a = before.get(key, "").splitlines(keepends=True)
        b = after.get(key, "").splitlines(keepends=True)
        if a != b:
            diff_parts.extend(difflib.unified_diff(
                a, b, "a/%s" % key, "b/%s" % key))
    return bool(diff_parts), "".join(diff_parts), notes


def stage_candidate(run_dir):
    """Copy skills/ to candidate_skills/ for a gated trial."""
    run_dir = Path(run_dir)
    cand = run_dir / "candidate_skills"
    if cand.exists():
        shutil.rmtree(cand)
    shutil.copytree(run_dir / "skills", cand)
    return cand


def promote_candidate(run_dir):
    """The candidate passed the gate: it becomes the skills layer."""
    run_dir = Path(run_dir)
    skills = run_dir / "skills"
    shutil.rmtree(skills)
    shutil.copytree(run_dir / "candidate_skills", skills)


def record_skill_impact(run_dir, *, iteration, proposal, val_score,
                        best_before, outcome, diff, author="proposer"):
    """The audit trail: written by the harness only, never by a model.
    `author` records who made the proposal — the proposer role, or the
    human owner (user proposals face the same gate)."""
    who = "" if author == "proposer" else " (author: %s)" % author
    entry = [
        "\n## Iteration %d — %s `%s` — **%s**%s"
        % (iteration, proposal.get("action"),
           proposal.get("name", "-"), outcome, who),
        "- validation score: %s (best before: %.4f)"
        % (val_score, best_before),
    ]
    if diff:
        entry += ["", "```diff", diff.rstrip("\n"), "```"]
    with (Path(run_dir) / "wiki" / "skill-impact.md").open(
            "a", encoding="utf-8") as f:
        f.write("\n".join(entry) + "\n")
