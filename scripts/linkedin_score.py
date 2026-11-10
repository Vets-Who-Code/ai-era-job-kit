#!/usr/bin/env python3
"""LinkedIn score: step 2 of the scoring chain.

Scores your own profile text against the lane and against your portfolio record. It never logs in
to LinkedIn or scrapes it: paste your profile into templates/linkedin-profile.txt, or save your
profile as a PDF from LinkedIn and pass that.

  python3 linkedin_score.py --profile linkedin.txt --market resume-score.json \\
      [--portfolio <repo>/portfolio.json] [--resume resume.pdf] [--json linkedin-score.json] [--md linkedin-score.md]
  (or --onet 15-1252.00 for a live O*NET pull instead of --market)

Why these checks (references/ats-research.md and references/sources.md):
  - LinkedIn Recruiter filters on skills, job title, location and open to work, and standardizes titles
    and skills [vendor: LinkedIn, Using Advanced AI-Assisted Search]. So headline, location and skills are
    filters you match or miss.
  - LinkedIn is for evidence, not applying; recruiters compare it to your resume, and a mismatch is a red
    flag [VWC: Jerome, Feb 3 2026]. Rankers read LinkedIn alongside the resume (Oct 7 2026).
  - The profile mirrors the portfolio record (the single source of truth).
  - LinkedIn data reaches the ATS (Apply Connect sends profile and skills-match data, references/sources.md),
    so the result carries skill_evidence: lane skills shown in Experience, Projects or Featured. Step 1 and
    the composite use it to confirm a skill as proven.
The weights are a VWC rubric, not LinkedIn's. LinkedIn doesn't publish how it ranks profiles.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from jobdata import docs, lexicon  # noqa: E402
from jobdata import market as mk  # noqa: E402
from jobdata.net import FetchError  # noqa: E402

HEADS = {
    "headline": r"headline",
    "location": r"location",
    "open_to_work": r"open to work",
    "about": r"about|summary",
    "experience": r"experience",
    "projects": r"projects",
    "skills": r"(?:top )?skills",
    "featured": r"featured",
    "education": r"education",
    "contact": r"contact",
    "certifications": r"licenses? (?:&|and) certifications|certifications",
}
# A heading is the name alone on its line, or the name, a colon and the value. "Experience with Kubernetes
# is my strength" is a sentence, not a heading.
HEAD_RE = re.compile(r"^\s*(" + "|".join(HEADS.values()) + r")\s*(?::\s*(.*))?$", re.I)
PAGE_FOOTER = re.compile(r"^page \d+ of \d+$", re.I)
CONTACT_LINE = re.compile(r"@|linkedin\.com|www\.|https?://|\(")
URL = re.compile(r"https?://\S+|\b[\w-]+\.(?:dev|io|com|me|app|net|org)\b", re.I)
# LinkedIn's Save to PDF leaves these out, so a PDF can't fail them: they're skipped, and the report says so.
NOT_IN_PDF = {"featured": "Featured", "open_to_work": "Open to Work"}


def split_profile(text: str) -> dict[str, str]:
    """Return {section: text}. Works on the kit template and on LinkedIn's Save to PDF (read in reading
    order: the sidebar with Contact and Top Skills, then name, headline, location, Summary, Experience)."""
    segs: list[tuple[str, list[str]]] = [("top", [])]
    for raw in text.splitlines():
        line = raw.strip()
        if not line or PAGE_FOOTER.match(line):
            continue
        m = HEAD_RE.match(line)
        if m:
            key = next(k for k, v in HEADS.items() if re.fullmatch(v, m.group(1), re.I))
            segs.append((key, [m.group(2).strip()] if (m.group(2) or "").strip() else []))
            continue
        segs[-1][1].append(line)
    keys = [k for k, _ in segs]
    if "headline" not in keys:
        # No label: name, headline and location are the last lines before About (or Experience). In the PDF
        # they follow the sidebar, so they sit at the end of whichever sidebar section came last.
        at = next((i for i, k in enumerate(keys) if k in ("about", "experience") and i > 0), None)
        if at is not None:
            before = segs[at - 1][1]
            last = before[-3:]
            tail = [l for l in last if not CONTACT_LINE.search(l)]
            if len(tail) >= 2:
                del before[len(before) - len(last):]
                segs.append(("headline", [tail[-2] if len(tail) == 3 else tail[-1]]))
                if len(tail) == 3 and "location" not in keys:
                    segs.append(("location", [tail[-1]]))
    out: dict[str, list[str]] = {}
    for k, lines in segs:
        out.setdefault(k, []).extend(lines)
    return {k: "\n".join(v) for k, v in out.items() if v}


def score(text: str, market: dict, record: dict | None = None, resume: str | None = None,
          from_pdf: bool = False) -> dict:
    s = split_profile(text)
    skipped = [name for key, name in NOT_IN_PDF.items() if from_pdf and not s.get(key)]
    head, about = s.get("headline", ""), s.get("about", "")
    exp = s.get("experience", "") + "\n" + s.get("projects", "")
    skills_txt = s.get("skills", "")
    prof = (record or {}).get("profile", {})
    role = prof.get("target_role", "")
    C = mk.check
    checks = []

    # 1 Headline: target role + stack + one differentiator, in the posting's words [VWC]; titles are a filter [vendor]
    role_words = {w for w in re.findall(r"[a-z]+", role.lower()) if len(w) > 2}
    head_words = set(re.findall(r"[a-z]+", head.lower()))
    head_sk = lexicon.find_skills(head, market["vocab"])
    checks += [
        C("Headline", "Headline is filled in", len(head.split()) >= 3, head[:100], 2,
          "Write a headline: target role, stack, one differentiator."),
        C("Headline", "Headline names your target role" + (f" ({role})" if role else ""),
          bool(role_words) and role_words <= head_words, head[:100], 3,
          f"Lead the headline with your target role in the posting's words: \"{role or 'Software Engineer'}\"."),
        C("Headline", "Headline names 2+ lane skills", len(head_sk) >= 2, ", ".join(sorted(head_sk)), 2,
          "Add your two strongest proven lane skills to the headline."),
    ]
    # 2 Location is a recruiter filter [vendor]
    loc = s.get("location", "")
    rloc = prof.get("location", "")
    checks.append(C("Filters", "Location set" + (" and matches your record" if rloc else ""),
                    bool(loc) and (not rloc or rloc.split(",")[0].lower() in loc.lower() or "remote" in (loc + rloc).lower()),
                    loc, 2, "Set the metro you're targeting, the same one as on your resume and portfolio."))
    # 3 Open to Work titles match the headline [VWC]
    otw = s.get("open_to_work", "")
    if "Open to Work" not in skipped:
        checks.append(C("Filters", "Open to Work lists the titles you apply to", bool(otw) and (not role_words or role_words & set(re.findall(r"[a-z]+", otw.lower()))),
                        otw[:100], 1, "Turn on Open to Work with the exact titles you apply to (recruiters only, if you're employed)."))
    # 4 Skills: the skills you can prove, named the market's way [vendor: skills are a filter]
    share, found, missing = mk.coverage(skills_txt, market, top=10)
    checks.append(C("Skills", "Skills section covers the lane's top 10", share >= 0.6, f"{round(100 * share)}% weighted; missing {', '.join(missing[:5])}", 3,
                    f"Add the lane skills you can prove, named the market's way: {', '.join(missing[:5])}."))
    if record:
        # Match both sides through the same aliases: "Postgres" in the record proves "PostgreSQL" on LinkedIn
        proven = lexicon.find_skills(" , ".join(x for a in record.get("artifacts", []) for x in a.get("skills", [])), market["vocab"])
        listed = lexicon.find_skills(skills_txt, market["vocab"])
        unproven = sorted(listed - proven)
        checks.append(C("Skills", "Every listed skill is proven by a portfolio artifact", not unproven, ", ".join(unproven[:6]), 2,
                        f"Prove these in the portfolio first, or drop them: {', '.join(unproven[:6])}."))
    # 5 Featured: flagship case study, live app, writing [VWC]
    feat = s.get("featured", "")
    if "Featured" not in skipped:
        checks.append(C("Proof", "Featured has links", len(URL.findall(feat)) >= 1, f"{len(URL.findall(feat))} links", 2,
                        "Feature your flagship case study, the live app and one piece of writing."))
    # 6 About: what you build and for whom; proof with numbers; what you want next [VWC]
    sentences = [x for x in re.split(r"(?<=[.!?])\s+", about) if len(x.split()) >= 4]
    site = (record or {}).get("links", {}).get("site", "")
    checks += [
        C("About", "About has 3+ sentences", len(sentences) >= 3, f"{len(sentences)} sentences", 2,
          "Write three short first-person paragraphs: what you build and for whom, proof, what you want next."),
        C("About", "About gives proof with a number", lexicon.has_number(URL.sub(" ", about)), "", 2,
          "Name two artifacts with outcomes and numbers that also appear in your portfolio."),
        C("About", "About points to your portfolio", bool(URL.search(about)) or (bool(site) and site.split("//")[-1] in about), "", 1,
          "Link your portfolio site in About."),
    ]
    # 7 Experience mirrors the resume [VWC: a mismatch is a red flag]
    exp_lines = [l for l in exp.splitlines() if len(l.split()) >= 5]
    numbered = [l for l in exp_lines if lexicon.has_number(re.sub(r"\b(19|20)\d{2}\b", "", l))]
    checks.append(C("Experience", "Experience lines show results with numbers", len(numbered) >= max(1, len(exp_lines) // 3),
                    f"{len(numbered)} of {len(exp_lines)} lines", 2, "Mirror your resume's strongest bullets, numbers included."))
    if record:
        titles = [e.get("title", "") for e in record.get("experience", []) if e.get("title")]
        miss = [t for t in titles if t.lower() not in exp.lower()]
        checks.append(C("Experience", "Titles match the portfolio record", not miss, ", ".join(miss[:4]), 2,
                        f"Use the same titles, orgs and dates as your record and resume: {', '.join(miss[:4])}."))
    if resume:
        rs = lexicon.find_skills(resume, market["vocab"])
        ls = lexicon.find_skills(text, market["vocab"])
        gap = sorted((rs - ls))[:6]
        checks.append(C("Consistency", "Every lane skill on the resume also shows on LinkedIn", not gap, ", ".join(gap), 2,
                        f"Add to LinkedIn (skills or experience): {', '.join(gap)}."))
    # Evidence for step 1 and the composite: skills shown in Experience, Projects or Featured, not the Skills list
    evidence = {}
    for label, body in (("Experience", s.get("experience", "")), ("Projects", s.get("projects", "")), ("Featured", feat)):
        for sk in lexicon.find_skills(body, market["vocab"]):
            evidence.setdefault(sk, []).append(f"LinkedIn {label}")
    return {"surface": "linkedin", "score": mk.weighted(checks), "checks": checks, "market": market["source"],
            "coverage_top10": round(share, 2), "missing_top10": missing, "skill_evidence": evidence,
            "skipped": skipped}


def report_md(r: dict) -> str:
    L = [f"# LinkedIn score (step 2 of the chain): {r['score']} / 100", "", f"Target: {r['market']}.", "",
         "| Section | Check | OK | Detail |", "|---|---|---|---|"]
    L += [f"| {c['section']} | {c['check']} | {'yes' if c['pass'] else 'no'} | {c['detail'][:70]} |" for c in r["checks"]]
    fails = sorted((c for c in r["checks"] if not c["pass"]), key=lambda c: -c["weight"])
    if fails:
        L += ["", "## Fix first", *[f"{i}. {c['fix']}" for i, c in enumerate(fails[:5], 1)]]
    if r.get("skipped"):
        L += ["", f"Not checked: {' and '.join(r['skipped'])}. LinkedIn's PDF leaves them out. Paste them into "
              "templates/linkedin-profile.txt and rerun to score them."]
    L += ["", "Rubric weights are VWC's, not LinkedIn's. LinkedIn doesn't publish how it ranks profiles."]
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", required=True, help="your profile as .txt (templates/linkedin-profile.txt) or LinkedIn's PDF")
    ap.add_argument("--market", help="resume-score.json from step 1")
    ap.add_argument("--onet")
    ap.add_argument("--portfolio")
    ap.add_argument("--resume")
    ap.add_argument("--json")
    ap.add_argument("--md")
    a = ap.parse_args(argv)
    try:
        text = docs.read_text(a.profile, layout=False)  # reading order: the PDF has a sidebar
        record = json.loads(pathlib.Path(a.portfolio).read_text()) if a.portfolio else None
        resume = docs.read_text(a.resume) if a.resume else None
        market = mk.load(a.market, a.onet or (record or {}).get("profile", {}).get("onet_code"))
    except FetchError as e:
        print(f"STOPPED: {e}", file=sys.stderr)
        return 3
    except (OSError, ValueError, RuntimeError) as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    r = score(text, market, record, resume, from_pdf=a.profile.lower().endswith(".pdf"))
    md = report_md(r)
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(r, indent=2))
    if a.md:
        pathlib.Path(a.md).write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
