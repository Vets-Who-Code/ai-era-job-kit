#!/usr/bin/env python3
"""Two scores and an improvement plan: steps 5 and 6 of the scoring chain.

  # Step 5: a machine read and a human read across the four surfaces, plus the resume gate
  python3 scorecard.py composite --resume resume-score.json --linkedin linkedin-score.json \\
      --github github-score.json --portfolio portfolio-score.json [--sync sync.md] \\
      [--machine-weights resume=40,linkedin=35,github=15,portfolio=10] \\
      [--human-weights portfolio=35,github=30,resume=20,linkedin=15] [--gate 70] \\
      [--screen screen.json ...] [--json composite.json] [--md composite.md]

  # Step 6: the steps to improve each section, biggest gain first
  python3 scorecard.py plan --composite composite.json [--md plan.md]

Every scorer in the chain writes the same shape:
  {"surface": ..., "score": 0-100, "checks": [{"section","check","pass","detail","weight","fix"}]}

Two reads, because two kinds of reader see you in order:
  - Machine read (ATS and AI screeners): resume 40, LinkedIn 35, GitHub 15, portfolio 10. They read text
    literally: titles, keywords, dates, structure, match to the posting.
  - Human read (recruiter, hiring manager, engineers): portfolio 35, GitHub 30, resume 20, LinkedIn 15.
    People skim for proof: a live demo, real impact, a clear story, recent commits.
  - Resume gate: a resume that scores under the gate (default 70) on its own text, or that fails the
    parse gate, is flagged whatever either total says. A weak resume means no human ever sees the rest.
    The gate reads text_score (the resume alone), because the gate is about the file a screener parses.
  - Screen Grades (screen_grade.py grade --out) are the one score modeled on vendor documents. They are
    per posting, so they sit beside the two reads with no invented weight; a C or D is flagged.
  - The LinkedIn and GitHub share of the machine read rests on a chat-only claim (references/ats-research.md):
    no vendor documents which systems score them. The report says so and shows the resume alone beside it.
These weights and the gate are a VWC design judgment (chosen Nov 6 2026), not research and not any
employer's. Employers don't publish theirs. Change them with --machine-weights, --human-weights and --gate.
A missing surface is left out of both reads and the rest are reweighted; the report says the scores are partial.
The sync check (sync_check.py) is reported beside the scores. It doesn't change them.
Before either read, the resume is rescored with the GitHub and LinkedIn evidence: a skill is proven only
when a resume bullet with a number names it AND recent GitHub work or LinkedIn shows it (resume_score.py).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import resume_score  # noqa: E402

READS = {
    "machine": {"resume": 40, "linkedin": 35, "github": 15, "portfolio": 10},
    "human": {"portfolio": 35, "github": 30, "resume": 20, "linkedin": 15},
}
READ_NAME = {"machine": "Machine read (ATS and AI screeners)", "human": "Human read (recruiter, hiring manager, engineers)"}
RESUME_GATE = 70  # VWC design judgment; change with --gate
WEIGHTS_SOURCE = "VWC design judgment, Nov 6 2026 (not research; configurable)"
SKILL_FOR = {
    "resume": ("resume-rebuilder", "step 7 rebuilds the resume to spec from your portfolio"),
    "linkedin": ("linkedin-scorer", "fix the profile, then rescore"),
    "github": ("github-scorer", "fix the pinned repos and profile, then rescore"),
    "portfolio": ("portfolio-scorer", "fix the site and artifacts, then rescore"),
}
ORDER = ["resume", "linkedin", "github", "portfolio"]
NAME = {"resume": "Resume", "linkedin": "LinkedIn", "github": "GitHub", "portfolio": "Portfolio"}


def parse_weights(s: str | None, read: str = "machine") -> dict[str, float]:
    w = dict(READS[read])
    if not s:
        return w
    for part in s.split(","):
        k, _, v = part.partition("=")
        k = k.strip().lower()
        if k not in w:
            raise ValueError(f"Unknown surface in --{read}-weights: {k}. Use github, linkedin, resume, portfolio.")
        w[k] = float(v)
    if sum(w.values()) <= 0:
        raise ValueError("Weights must add up to more than 0.")
    return w


def load_surface(path: str, expect: str) -> dict:
    r = json.loads(pathlib.Path(path).read_text())
    if r.get("surface") != expect:
        raise ValueError(f"{path} is not a {expect} score (surface = {r.get('surface')!r}).")
    return r


def read_score(surfaces: dict[str, dict], weights: dict[str, float]) -> dict:
    """One weighted read over the surfaces that have a score."""
    scored = {k: v for k, v in surfaces.items() if v.get("score") is not None}
    tot = sum(weights[k] for k in scored)
    score = round(sum(weights[k] * scored[k]["score"] for k in scored) / tot) if tot else None
    rows = []
    for k in ORDER:
        r = surfaces.get(k)
        status = "missing" if r is None else ("blocked" if r.get("score") is None else "scored")
        rows.append({"surface": k, "weight": weights[k], "score": None if r is None else r.get("score"), "status": status,
                     "gap_points": round(weights[k] * (100 - r["score"]) / 100, 1) if status == "scored" else None})
    return {"score": score, "weights": weights, "rows": rows}


def resume_gate(surfaces: dict[str, dict], threshold: float) -> dict:
    r = surfaces.get("resume")
    if r is None:
        return {"threshold": threshold, "resume_score": None, "passed": None,
                "note": "Resume not scored, so the gate is unknown. Run step 1."}
    if r.get("score") is None:
        return {"threshold": threshold, "resume_score": None, "passed": False,
                "note": "The resume failed the parse gate. A screener can't read it, so no human sees the rest. Fix the format first."}
    own = r.get("text_score", r["score"])  # the resume alone, before GitHub or LinkedIn back anything
    ok = own >= threshold
    return {"threshold": threshold, "resume_score": own, "passed": ok,
            "note": "Resume clears the gate." if ok else
            f"Resume scores {own} on its own text, under the gate of {threshold:g}. A weak resume means no human sees your GitHub or portfolio, whatever the totals say. Fix it first."}


def screen_summary(r: dict, path: str = "") -> dict:
    """One Screen Grade (screen_grade.py grade --out), cut down to what the composite reports."""
    if "grade" not in r or "rows" not in r:
        raise ValueError(f"{path or 'file'} is not a Screen Grade report. Write one with screen_grade.py grade --out.")
    return {"posting": (r.get("title") or {}).get("posting_title") or path, "grade": r["grade"],
            "basic": r.get("basic", ""), "preferred": r.get("preferred", ""), "flag": r["grade"] in ("C", "D", "No grade"),
            "not_met_basic": [x["qualification"] for x in r["rows"] if x["kind"] == "basic" and not x["met"]]}


def composite(surfaces: dict[str, dict], weights: dict[str, dict] | None = None, sync: dict | None = None,
              gate: float = RESUME_GATE, screens: list[dict] | None = None) -> dict:
    weights = weights or {k: dict(v) for k, v in READS.items()}
    res = surfaces.get("resume")
    if res and res.get("skills"):
        # Proven needs outside proof: rescore the resume with the GitHub and LinkedIn evidence
        surfaces = dict(surfaces, resume=resume_score.corroborate(
            json.loads(json.dumps(res)), resume_score.merge_evidence(surfaces.get("linkedin"), surfaces.get("github"))))
    reads = {k: read_score(surfaces, weights[k]) for k in READS}
    missing = [k for k in ORDER if k not in surfaces]
    blocked = [k for k, v in surfaces.items() if v.get("score") is None]
    return {"surface": "composite", "machine": reads["machine"], "human": reads["human"],
            "gate": resume_gate(surfaces, gate), "partial": bool(missing or blocked), "missing": missing,
            "blocked": blocked, "weights_source": WEIGHTS_SOURCE, "sync": sync, "screens": screens or [],
            "inputs": surfaces}


def sync_summary(md_text: str) -> dict:
    """Read sync_check.py's markdown report: how many mismatches it lists under 'Fix these'."""
    fixes, on = [], False
    for line in md_text.splitlines():
        if line.startswith("## "):
            on = line.lower().startswith("## fix these")
            continue
        cells = [x.strip() for x in line.strip().strip("|").split("|")] if on and line.startswith("|") else []
        if len(cells) >= 4 and cells[0] not in ("Area",) and not set(cells[0]) <= {"-"}:
            fixes.append(f"{cells[0]} ({cells[2]}): {cells[3]}")
    return {"in_sync": not fixes, "fixes": fixes}


def plan(comp: dict, per_surface: int = 5) -> dict:
    """Step 6: a failed resume gate goes first; then surfaces by points left, averaged over both reads."""
    gaps = {}
    for read in READS:
        for row in comp[read]["rows"]:
            if row["gap_points"] is not None:
                gaps[row["surface"]] = gaps.get(row["surface"], 0) + row["gap_points"] / len(READS)
    gate_failed = comp["gate"]["passed"] is False
    status = {row["surface"]: row["status"] for row in comp["machine"]["rows"]}

    def key(k):
        if k == "resume" and gate_failed:
            return (0, 0)
        return (1, -gaps[k]) if k in gaps else (2, 0)

    steps = []
    for k in sorted(ORDER, key=key):
        skill, how = SKILL_FOR[k]
        st = status[k]
        if st != "scored":
            first = ("Fix the resume format first: a screener that can't parse it gives no grade (see the parse checks)."
                     if st == "blocked" else f"Run the {NAME[k]} scorer so this surface counts.")
            steps.append({"surface": k, "skill": skill, "gap_points": None, "status": st, "fixes": [first], "lift_skills": []})
            continue
        r = comp["inputs"][k]
        fails = sorted((c for c in r.get("checks", []) if not c.get("pass") and c.get("fix")), key=lambda c: -float(c.get("weight") or 0))
        lifts = []
        if k == "resume":
            order = ["proven", "applied", "listed", "stale", "none"]  # ties: what's already on the resume first
            lifts = [{"skill": s["skill"], "grade": s["grade"], "lift": s["lift"]}
                     for s in sorted(r.get("skills", []), key=lambda s: (-s.get("lift", 0), order.index(s.get("grade", "none"))))
                     if s.get("lift", 0) > 0][:per_surface]
            fails = [c for c in fails if c.get("section") != "Evidence"]  # shown once, as lift skills
        steps.append({"surface": k, "skill": skill, "how": how, "score": r["score"], "gap_points": round(gaps[k], 1),
                      "status": "scored", "gate": k == "resume" and gate_failed,
                      "fixes": [c["fix"] for c in fails[:per_surface]], "lift_skills": lifts})
    sync = comp.get("sync") or {}
    return {"surface": "plan", "machine": comp["machine"]["score"], "human": comp["human"]["score"], "gate": comp["gate"],
            "partial": comp["partial"], "steps": steps, "sync_fixes": sync.get("fixes", []),
            "screen_fixes": [f"{s['posting'] or 'posting'} (grade {s['grade']}): {q}" for s in comp.get("screens") or []
                             for q in s["not_met_basic"]],
            "next": "Then run resume-rebuilder (step 7) and rescore the whole chain."}


def _fmt(x) -> str:
    return "n/a" if x is None else str(x)


def composite_md(c: dict) -> str:
    part = " (partial)" if c["partial"] else ""
    L = [f"# Two scores (step 5 of the chain){part}", "",
         f"- Machine read: {_fmt(c['machine']['score'])} / 100",
         f"- Human read: {_fmt(c['human']['score'])} / 100",
         f"- Resume gate ({c['gate']['threshold']:g}): " + {True: "passed", False: "FLAGGED", None: "unknown"}[c["gate"]["passed"]]
         + f". {c['gate']['note']}", ""]
    for read in READS:
        L += [f"## {READ_NAME[read]}", "", "| Surface | Weight | Score | Points left |", "|---|---|---|---|"]
        for r in c[read]["rows"]:
            sc = {"missing": "not run", "blocked": "no score (format)"}.get(r["status"], str(r["score"]))
            L.append(f"| {NAME[r['surface']]} | {r['weight']:g} | {sc} | {'' if r['gap_points'] is None else r['gap_points']} |")
        L.append("")
    for s in c.get("screens") or []:
        L.append(f"- Screen Grade, {s['posting'] or 'posting'}: {s['grade']} (basic {s['basic']}, preferred {s['preferred']})"
                 + (". FLAGGED: fix the basic qualifications not met before you apply." if s["flag"] else "."))
    if c.get("screens"):
        L.append("  Screen Grades follow the vendors' documented method. They are per posting, so they aren't weighted into either read.")
        L.append("")
    L.append(f"Weights and gate: {c['weights_source']}. Not any employer's; employers don't publish theirs.")
    res = (c.get("inputs") or {}).get("resume") or {}
    if any(k in (c.get("inputs") or {}) for k in ("linkedin", "github")):
        L.append("The LinkedIn and GitHub share of the machine read rests on a chat-only claim (references/ats-research.md); "
                 "no vendor documents which systems score them." + (f" Resume alone: {res['score']} / 100." if res.get("score") is not None else ""))
    if (c.get("inputs") or {}).get("portfolio", {}).get("judgment_pass") is False:
        L.append("Portfolio score: automated checks only. Add the checklist pass (portfolio_audit.py --checklist) so the human read includes a human's judgment.")
    if c["missing"]:
        L.append(f"Not run: {', '.join(c['missing'])}. Both reads reweight the rest.")
    if c["sync"] is not None:
        L.append("Sync check: in sync." if c["sync"]["in_sync"] else f"Sync check: {len(c['sync']['fixes'])} mismatches (not in the scores; fix them in step 6).")
    return "\n".join(L)


def plan_md(p: dict) -> str:
    L = [f"# Improvement plan (step 6 of the chain)", "",
         f"Machine read: {_fmt(p['machine'])}. Human read: {_fmt(p['human'])}{' (partial)' if p['partial'] else ''}. Biggest gain first.", ""]
    if p["gate"]["passed"] is False:
        L += [f"Resume gate flagged: {p['gate']['note']}", ""]
    for i, s in enumerate(p["steps"], 1):
        gp = f", {s['gap_points']} points left (average of both reads)" if s.get("gap_points") is not None else ""
        gate = " · resume gate: fix this first" if s.get("gate") else ""
        L.append(f"## {i}. {NAME[s['surface']]}{gp}{gate} · use {s['skill']}")
        if s.get("lift_skills"):
            L.append("Prove these first (Experience or Projects bullet with a number):")
            L += [f"- {x['skill']}: now {x['grade']}, +{x['lift']} points" for x in s["lift_skills"]]
        L += [f"- {f}" for f in s["fixes"]] or ["- Nothing failing."]
        L.append("")
    if p.get("screen_fixes"):
        L += ["## Basic qualifications not met (per posting, fix before applying)", *[f"- {f}" for f in p["screen_fixes"]], ""]
    if p["sync_fixes"]:
        L += ["## Keep every surface in sync with portfolio.json", *[f"- {f}" for f in p["sync_fixes"]], ""]
    L.append(p["next"])
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("composite")
    for k in ORDER:
        c.add_argument(f"--{k}", help=f"{k}-score.json")
    c.add_argument("--sync", help="sync_check.py markdown report")
    c.add_argument("--screen", nargs="*", default=[], help="Screen Grade reports (screen_grade.py grade --out), one per posting")
    c.add_argument("--machine-weights", help="e.g. resume=40,linkedin=35,github=15,portfolio=10")
    c.add_argument("--human-weights", help="e.g. portfolio=35,github=30,resume=20,linkedin=15")
    c.add_argument("--gate", type=float, default=RESUME_GATE, help=f"resume score under this is flagged (default {RESUME_GATE})")
    c.add_argument("--json")
    c.add_argument("--md")
    p = sub.add_parser("plan")
    p.add_argument("--composite", required=True, help="composite.json from step 5")
    p.add_argument("--json")
    p.add_argument("--md")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "composite":
            surfaces = {k: load_surface(getattr(a, k), k) for k in ORDER if getattr(a, k)}
            if not surfaces:
                raise ValueError("Give at least one of --resume, --linkedin, --github, --portfolio.")
            sync = sync_summary(pathlib.Path(a.sync).read_text()) if a.sync else None
            w = {"machine": parse_weights(a.machine_weights, "machine"), "human": parse_weights(a.human_weights, "human")}
            screens = [screen_summary(json.loads(pathlib.Path(x).read_text()), x) for x in a.screen]
            out = composite(surfaces, w, sync, a.gate, screens)
            md = composite_md(out)
        else:
            out = plan(json.loads(pathlib.Path(a.composite).read_text()))
            md = plan_md(out)
    except (OSError, ValueError, KeyError) as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(out, indent=2))
    if a.md:
        pathlib.Path(a.md).write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
