#!/usr/bin/env python3
"""Sync check: keep your four sources of truth telling one story.

The portfolio (portfolio.json + brag/entries) is the master record. GitHub,
your resume and LinkedIn are built from it. This script reads all four and
lists every place they disagree, so you fix the portfolio first and
regenerate the rest.

  python3 sync_check.py --portfolio ~/code/portfolio/portfolio.json \\
      --resume ~/resumes/me-software-developer.pdf \\
      --linkedin ~/job-search/linkedin.txt --github yourhandle [--md sync.md]

--linkedin is a text file of your profile: copy the headline, About,
Experience and Featured sections into it (this script never logs in).
--github uses the GitHub CLI (https://cli.github.com, `gh auth login`); skip
it to check offline.

Checks
  - Headline / target role appears on the resume, LinkedIn and GitHub bio.
  - Each deployed artifact (depth 2+) appears on the resume and LinkedIn,
    and is pinned on GitHub.
  - Each experience entry (title + org) appears on the resume and LinkedIn.
  - Skills on the resume that no portfolio artifact proves.
  - Experience-length claims use only 5+ or 10+ and never more than 10+.
  - The portfolio site and GitHub links appear where readers look.

Exit codes: 0 in sync, 1 mismatches found, 2 bad input.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from jobdata import docs, lexicon  # noqa: E402

PINNED_Q = """query($login:String!){user(login:$login){bio websiteUrl
 pinnedItems(first:6,types:REPOSITORY){nodes{... on Repository{name url}}}}}"""


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9+#]+", " ", (s or "").lower()).strip()


def mentions(haystack: str, needle: str) -> bool:
    n = norm(needle)
    return bool(n) and f" {n} " in f" {norm(haystack)} "


def artifact_mentioned(text: str, art: dict) -> bool:
    name = art.get("name", "")
    variants = {name, name.replace("-", " "), name.replace("_", " ")}
    if any(mentions(text, v) for v in variants if v):
        return True
    url = (art.get("url") or "").rstrip("/")
    return bool(url) and url.lower() in (text or "").lower()


def github_profile(login: str) -> tuple[dict | None, str]:
    if not shutil.which("gh"):
        return None, "GitHub CLI not installed; GitHub checks skipped"
    r = subprocess.run(["gh", "api", "graphql", "-f", f"query={PINNED_Q}", "-f", f"login={login}"],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return None, f"GitHub lookup failed ({r.stderr.strip()[:120]}); GitHub checks skipped"
    user = (json.loads(r.stdout).get("data") or {}).get("user")
    if not user:
        return None, f"GitHub user {login!r} not found; GitHub checks skipped"
    return user, ""


def check(record: dict, resume: str | None, linkedin: str | None, gh: dict | None) -> list[dict]:
    """Return findings: {area, item, surface, ok, fix}."""
    out: list[dict] = []
    prof = record.get("profile") or {}
    links = record.get("links") or {}
    surfaces = {"resume": resume, "LinkedIn": linkedin}

    def add(area, item, surface, ok, fix=""):
        out.append({"area": area, "item": item, "surface": surface, "ok": bool(ok), "fix": "" if ok else fix})

    role = prof.get("target_role") or ""
    if role:
        for sname, text in surfaces.items():
            if text is not None:
                add("Headline", role, sname, mentions(text, role),
                    f"Say \"{role}\" near the top of your {sname}, matching portfolio.json.")
        if gh is not None:
            add("Headline", role, "GitHub", mentions(gh.get("bio") or "", role),
                f"Put \"{role}\" in your GitHub bio.")

    pinned = {((n or {}).get("url") or "").rstrip("/").lower() for n in ((gh or {}).get("pinnedItems") or {}).get("nodes", [])}
    for art in record.get("artifacts", []):
        if (art.get("depth") or 0) < 2:
            continue
        nm = art.get("name", "artifact")
        for sname, text in surfaces.items():
            if text is not None:
                add("Artifacts", nm, sname, artifact_mentioned(text, art),
                    f"Add {nm} with its live link to your {sname} (Projects or Featured).")
        if gh is not None and art.get("repo"):
            add("Artifacts", nm, "GitHub", art["repo"].rstrip("/").lower() in pinned,
                f"Pin {art['repo']} on your GitHub profile.")

    for job in record.get("experience", []):
        label = f"{job.get('title', '')} at {job.get('org', '')}".strip()
        for sname, text in surfaces.items():
            if text is None:
                continue
            ok = mentions(text, job.get("title", "")) and mentions(text, job.get("org", ""))
            add("Experience", label, sname, ok,
                f"Use the same title and organization on your {sname} as in portfolio.json.")

    if resume is not None:
        vocab = lexicon.build_vocab()
        skills_txt, _ = docs.split_skills_section(resume)
        claimed = lexicon.find_skills(skills_txt or resume, vocab)
        proven = {s for a in record.get("artifacts", []) if (a.get("depth") or 0) >= 2
                  for s in lexicon.find_skills(" ".join(a.get("skills", [])), vocab)}
        for s in sorted(claimed - proven):
            add("Skills", s, "resume", False,
                f"Prove {s} with a portfolio artifact, or move it out of your skills list.")
        for m in re.finditer(r"\b(\d{1,2})\+?\s*(?:years|yrs)\b", resume, re.I):
            n = int(m.group(1))
            add("Years", m.group(0), "resume", n in (5, 10),
                "Use only \"5+\" or \"10+\" years, and never more than 10+.")

    for key, label in (("site", "portfolio site"), ("github", "GitHub")):
        url = (links.get(key) or "").replace("https://", "").replace("http://", "").rstrip("/").lower()
        if not url:
            continue
        for sname, text in surfaces.items():
            if text is not None:
                add("Links", label, sname, url in (text or "").lower(),
                    f"Add your {label} link ({links[key]}) to your {sname}.")
    if gh is not None and links.get("site"):
        site = links["site"].rstrip("/").lower()
        add("Links", "portfolio site", "GitHub", (gh.get("websiteUrl") or "").rstrip("/").lower() == site,
            f"Set your GitHub profile website to {links['site']}.")
    return out


def report(findings: list[dict], notes: list[str]) -> str:
    bad = [f for f in findings if not f["ok"]]
    good = len(findings) - len(bad)
    L = ["# Sources of truth: sync check", "",
         f"{good} of {len(findings)} checks agree with your portfolio." if findings else "Nothing to check.", ""]
    for n in notes:
        L.append(f"- note: {n}")
    if notes:
        L.append("")
    if not bad:
        L.append("Everything matches. Rerun after each Friday Setup or resume change.")
        return "\n".join(L)
    L += ["## Fix these (portfolio first, then regenerate the rest)", "",
          "| Area | Item | Where | Fix |", "|---|---|---|---|"]
    order = ["Headline", "Artifacts", "Experience", "Links", "Skills", "Years"]
    for f in sorted(bad, key=lambda x: (order.index(x["area"]) if x["area"] in order else 99, x["item"])):
        L.append(f"| {f['area']} | {f['item']} | {f['surface']} | {f['fix']} |")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--portfolio", required=True, help="portfolio.json (the master record)")
    ap.add_argument("--resume", help="resume file (.pdf, .docx, .txt, .md)")
    ap.add_argument("--linkedin", help="text file with your LinkedIn headline, About, Experience, Featured")
    ap.add_argument("--github", help="GitHub username")
    ap.add_argument("--md", help="also write the report to this file")
    a = ap.parse_args(argv)

    try:
        record = json.loads(pathlib.Path(a.portfolio).expanduser().read_text())
    except (OSError, json.JSONDecodeError) as e:
        print(f"Can't read {a.portfolio}: {e}", file=sys.stderr)
        return 2
    if not (a.resume or a.linkedin or a.github):
        ap.error("give at least one of --resume, --linkedin, --github")
    notes: list[str] = []
    resume = docs.read_text(str(pathlib.Path(a.resume).expanduser())) if a.resume else None
    linkedin = pathlib.Path(a.linkedin).expanduser().read_text() if a.linkedin else None
    gh = None
    if a.github:
        gh, note = github_profile(a.github)
        if note:
            notes.append(note)
    md = report(check(record, resume, linkedin, gh), notes)
    if a.md:
        pathlib.Path(a.md).write_text(md)
    print(md)
    return 1 if "## Fix these" in md else 0


if __name__ == "__main__":
    sys.exit(main())
