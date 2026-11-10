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
HEAD_RE = re.compile(r"^\s*(" + "|".join(HEADS.values()) + r")\s*:?\s*(.*)$", re.I)
NUMBER = re.compile(r"\d")
URL = re.compile(r"https?://\S+|\b[\w-]+\.(?:dev|io|com|me|app|net|org)\b", re.I)


def split_profile(text: str) -> dict[str, str]:
    """Return {section: text}. Works on the kit template and on LinkedIn's Save to PDF layout."""
    out: dict[str, list[str]] = {}
    cur = "top"
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = HEAD_RE.match(line)
        if m and len(line) <= 60 + len(m.group(2)):
            key = next(k for k, v in HEADS.items() if re.fullmatch(v, m.group(1), re.I))
            cur = key
            if m.group(2).strip():
                out.setdefault(cur, []).append(m.group(2).strip())
            continue
        out.setdefault(cur, []).append(line)
    sec = {k: "\n".join(v) for k, v in out.items()}
    if "headline" not in sec and "top" in sec:  # LinkedIn PDF: name, then headline, then location
        top = [l for l in sec["top"].splitlines() if not re.search(r"@|linkedin\.com|www\.|\(", l)]
        if len(top) >= 2:
            sec["headline"] = top[1]
        if len(top) >= 3 and "location" not in sec:
            sec["location"] = top[2]
    return sec


def score(text: str, market: dict, record: dict | None = None, resume: str | None = None) -> dict:
    s = split_profile(text)
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
    checks.append(C("Filters", "Open to Work lists the titles you apply to", bool(otw) and (not role_words or role_words & set(re.findall(r"[a-z]+", otw.lower()))),
                    otw[:100], 1, "Turn on Open to Work with the exact titles you apply to (recruiters only, if you're employed)."))
    # 4 Skills: the skills you can prove, named the market's way [vendor: skills are a filter]
    share, found, missing = mk.coverage(skills_txt, market, top=10)
    checks.append(C("Skills", "Skills section covers the lane's top 10", share >= 0.6, f"{round(100 * share)}% weighted; missing {', '.join(missing[:5])}", 3,
                    f"Add the lane skills you can prove, named the market's way: {', '.join(missing[:5])}."))
    if record:
        proven = {x.lower() for a in record.get("artifacts", []) for x in a.get("skills", [])}
        listed = lexicon.find_skills(skills_txt, market["vocab"])
        unproven = sorted(x for x in listed if x.lower() not in proven)
        checks.append(C("Skills", "Every listed skill is proven by a portfolio artifact", not unproven, ", ".join(unproven[:6]), 2,
                        f"Prove these in the portfolio first, or drop them: {', '.join(unproven[:6])}."))
    # 5 Featured: flagship case study, live app, writing [VWC]
    feat = s.get("featured", "")
    checks.append(C("Proof", "Featured has links", len(URL.findall(feat)) >= 1, f"{len(URL.findall(feat))} links", 2,
                    "Feature your flagship case study, the live app and one piece of writing."))
    # 6 About: what you build and for whom; proof with numbers; what you want next [VWC]
    sentences = [x for x in re.split(r"(?<=[.!?])\s+", about) if len(x.split()) >= 4]
    site = (record or {}).get("links", {}).get("site", "")
    checks += [
        C("About", "About has 3+ sentences", len(sentences) >= 3, f"{len(sentences)} sentences", 2,
          "Write three short first-person paragraphs: what you build and for whom, proof, what you want next."),
        C("About", "About gives proof with a number", bool(NUMBER.search(about)), "", 2,
          "Name two artifacts with outcomes and numbers that also appear in your portfolio."),
        C("About", "About points to your portfolio", bool(URL.search(about)) or (bool(site) and site.split("//")[-1] in about), "", 1,
          "Link your portfolio site in About."),
    ]
    # 7 Experience mirrors the resume [VWC: a mismatch is a red flag]
    exp_lines = [l for l in exp.splitlines() if len(l.split()) >= 5]
    numbered = [l for l in exp_lines if NUMBER.search(re.sub(r"(19|20)\d{2}", "", l))]
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
            "coverage_top10": round(share, 2), "missing_top10": missing, "skill_evidence": evidence}


def report_md(r: dict) -> str:
    L = [f"# LinkedIn score (step 2 of the chain): {r['score']} / 100", "", f"Target: {r['market']}.", "",
         "| Section | Check | OK | Detail |", "|---|---|---|---|"]
    L += [f"| {c['section']} | {c['check']} | {'yes' if c['pass'] else 'no'} | {c['detail'][:70]} |" for c in r["checks"]]
    fails = sorted((c for c in r["checks"] if not c["pass"]), key=lambda c: -c["weight"])
    if fails:
        L += ["", "## Fix first", *[f"{i}. {c['fix']}" for i, c in enumerate(fails[:5], 1)]]
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
        text = docs.read_text(a.profile)
        record = json.loads(pathlib.Path(a.portfolio).read_text()) if a.portfolio else None
        resume = docs.read_text(a.resume) if a.resume else None
        market = mk.load(a.market, a.onet or (record or {}).get("profile", {}).get("onet_code"))
    except FetchError as e:
        print(f"STOPPED: {e}", file=sys.stderr)
        return 3
    except (OSError, ValueError, RuntimeError) as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    r = score(text, market, record, resume)
    md = report_md(r)
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(r, indent=2))
    if a.md:
        pathlib.Path(a.md).write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
