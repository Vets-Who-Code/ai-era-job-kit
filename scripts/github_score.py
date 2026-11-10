#!/usr/bin/env python3
"""GitHub score: step 3 of the scoring chain.

Reads your public GitHub the way any tool can: the GitHub REST API, no account, no token, no agreement
(60 requests an hour; one run uses about 20). See references/sources.md. That limit is per IP address,
so a shared network shares it. If you hit it, wait an hour or set GITHUB_TOKEN (any token, no scopes
needed; `export GITHUB_TOKEN=$(gh auth token)` works) for 5,000 an hour. The data read is the same.

  python3 github_score.py --user yourhandle --repos repo-a,repo-b --market resume-score.json \\
      [--portfolio <repo>/portfolio.json] [--json github-score.json] [--md github-score.md]
  (or --onet 15-1252.00 for a live O*NET pull instead of --market)

Pass your pinned repos with --repos. The REST API doesn't list pins, so without it the script reads your
six most recently pushed non-fork repos and says so.

Why these checks (Jerome's rules, the github-scorer skill):
  - GitHub is how you show you exist; it should say what the portfolio says, in code.
  - Pin only manicured repos: fully built and working, each with a live demo (or a video demo).
  - Repo READMEs show the problem, decisions, tests, CI and evals; every claim points at code.
  - Rankers read GitHub alongside the resume (Oct 7 2026), so the repos should prove the lane's skills.
  - AI screeners score activity against the posting (Jerome, Nov 8 2026, chat only). So the result carries
    skill_evidence: each lane skill a pinned repo pushed in the last year shows. Step 1 and the composite
    use it to confirm a skill as proven.
The weights are a VWC rubric. GitHub publishes no hiring score.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from jobdata import lexicon  # noqa: E402
from jobdata import market as mk  # noqa: E402
from jobdata.net import FetchError, fetch_json  # noqa: E402

API = "https://api.github.com"
HDR = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
TEST_DIRS = re.compile(r"^(tests?|__tests__|spec|specs|e2e|cypress|playwright)$", re.I)
TEST_FILES = re.compile(r"(^|[._-])(test|spec)s?([._-]|$)|pytest\.ini|jest\.config|vitest\.config|playwright\.config", re.I)
DECISIONS = re.compile(r"\b(why|decision|tradeoff|trade-off|architecture|adr|chose|design)\b", re.I)


class GitHub:
    """Tiny REST client. Swap get() in tests."""

    def __init__(self):
        self.calls = 0
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        self.headers = dict(HDR, Authorization=f"Bearer {token}") if token else HDR

    def get(self, path: str):
        self.calls += 1
        return fetch_json(API + path, headers=self.headers, retries=2)

    def try_get(self, path: str):
        try:
            return self.get(path)
        except FetchError as e:
            if "404" in str(e):
                return None
            raise


def readme_text(gh: GitHub, owner: str, repo: str) -> str:
    d = gh.try_get(f"/repos/{owner}/{repo}/readme")
    if not d or "content" not in d:
        return ""
    try:
        return base64.b64decode(d["content"]).decode("utf8", "replace")
    except (ValueError, TypeError):
        return ""


def score(gh: GitHub, user: str, repos: list[str], market: dict, record: dict | None = None,
          today: dt.date | None = None, active_days: int = 365) -> dict:
    today = today or dt.date.today()
    cutoff = (today - dt.timedelta(days=90)).isoformat()
    C = mk.check
    u = gh.get(f"/users/{user}")
    all_repos = gh.get(f"/users/{user}/repos?per_page=100&sort=pushed") or []
    by_name = {r["name"].lower(): r for r in all_repos}
    note = ""
    if repos:
        picked = [by_name[n.lower()] for n in repos if n.lower() in by_name]
        lost = [n for n in repos if n.lower() not in by_name]
        if lost:
            note = f"Not found or not public: {', '.join(lost)}"
    else:
        picked = [r for r in all_repos if not r.get("fork")][:6]
        note = "Pins unknown: pass --repos with your pinned repos. Read the six most recently pushed instead."
    site = (record or {}).get("links", {}).get("site", "")
    blog = u.get("blog") or ""
    profile_readme = readme_text(gh, user, user)
    checks = [
        C("Profile", "Bio set", bool(u.get("bio")), (u.get("bio") or "")[:80], 1, "Write a one-line bio: what you build and your strongest skill."),
        C("Profile", "Website links your portfolio", bool(blog) and (not site or site.split("//")[-1].rstrip("/") in blog),
          blog, 2, f"Set your profile website to your portfolio{': ' + site if site else ''}."),
        C("Profile", "Profile README", len(profile_readme) >= 200, f"{len(profile_readme)} chars", 2,
          f"Create the {user}/{user} repo with a README: one line on what you build, three artifacts with outcomes and live links."),
        C("Profile", "Active in the last 90 days", any((r.get("pushed_at") or "") >= cutoff for r in all_repos),
          (all_repos[0].get("pushed_at") or "")[:10] if all_repos else "no public repos", 2,
          "Push real work. Merged PRs feed your Brag Database every Friday."),
        C("Pins", "Pinned repos given", bool(picked) and bool(repos), f"{len(picked)} repos", 2,
          "Pin only manicured repos, each fully built and working with a live or video demo."),
    ]
    corpus = [u.get("bio") or "", profile_readme]
    active_cut = (today - dt.timedelta(days=active_days)).isoformat()
    evidence: dict[str, list[str]] = {}
    for r in picked:
        n = r["name"]
        rd = readme_text(gh, user, n)
        root = gh.try_get(f"/repos/{user}/{n}/contents/") or []
        names = [x.get("name", "") for x in root if isinstance(x, dict)]
        has_tests = any(TEST_DIRS.match(x) or TEST_FILES.search(x) for x in names)
        wf = gh.try_get(f"/repos/{user}/{n}/contents/.github/workflows") if ".github" in names else None
        repo_text = [r.get("description") or "", " ".join(r.get("topics") or []), r.get("language") or "", rd]
        corpus += repo_text
        if (r.get("pushed_at") or "") >= active_cut and not r.get("fork"):
            for sk in lexicon.find_skills("\n".join(repo_text), market["vocab"]):
                evidence.setdefault(sk, []).append(f"GitHub {n}")
        checks += [
            C(n, "README explains it", len(rd) >= 1200, f"{len(rd)} chars", 2,
              f"{n}: write the README in this order: problem, why it matters, how it works, live link, how to run it."),
            C(n, "README shows decisions", bool(DECISIONS.search(rd)), "", 1, f"{n}: add the key decisions and tradeoffs, with links to the code."),
            C(n, "Live demo link", bool(r.get("homepage")), r.get("homepage") or "", 2, f"{n}: set the repo website to the live demo, or link a video demo."),
            C(n, "Description", bool(r.get("description")), (r.get("description") or "")[:60], 1, f"{n}: add a one-line description with the outcome."),
            C(n, "Tests in the repo", has_tests, "", 2, f"{n}: add tests, and say in the README how to run them."),
            C(n, "CI workflow", bool(wf), "", 2, f"{n}: add a GitHub Actions workflow that runs the tests."),
            C(n, "License", bool(r.get("license")), ((r.get("license") or {}).get("spdx_id") or ""), 1, f"{n}: choose a license."),
            C(n, "Topics", bool(r.get("topics")), ", ".join(r.get("topics") or [])[:60], 1, f"{n}: add topics named the way the market names your skills."),
            C(n, "Your own work, not a fork", not r.get("fork"), "", 1, f"{n}: unpin forks with no changes."),
        ]
    share, found, missing = mk.coverage("\n".join(corpus), market, top=10)
    checks.append(C("Lane", "Pinned repos prove the lane's top 10 skills", share >= 0.5,
                    f"{round(100 * share)}% weighted; missing {', '.join(missing[:5])}", 3,
                    f"Show these in a pinned repo (code, README, topics): {', '.join(missing[:5])}."))
    if record:
        arts = [a for a in record.get("artifacts", []) if a.get("repo")]
        unpinned = [a["name"] for a in arts if a["repo"].rstrip("/").split("/")[-1].lower() not in {p["name"].lower() for p in picked}]
        checks.append(C("Lane", "Portfolio artifacts are the pinned repos", not unpinned, ", ".join(unpinned[:4]), 2,
                        f"Pin the repos behind your portfolio artifacts: {', '.join(unpinned[:4])}."))
    return {"surface": "github", "score": mk.weighted(checks), "checks": checks, "user": user,
            "repos": [p["name"] for p in picked], "note": note, "market": market["source"],
            "coverage_top10": round(share, 2), "missing_top10": missing, "api_calls": gh.calls,
            "skill_evidence": evidence, "active_days": active_days}


def report_md(r: dict) -> str:
    L = [f"# GitHub score (step 3 of the chain): {r['score']} / 100", "",
         f"{r['user']} · repos read: {', '.join(r['repos']) or 'none'} · target: {r['market']}.", ""]
    if r["note"]:
        L += [f"Note: {r['note']}", ""]
    L += ["| Area | Check | OK | Detail |", "|---|---|---|---|"]
    L += [f"| {c['section']} | {c['check']} | {'yes' if c['pass'] else 'no'} | {c['detail'][:60]} |" for c in r["checks"]]
    fails = sorted((c for c in r["checks"] if not c["pass"]), key=lambda c: -c["weight"])
    if fails:
        L += ["", "## Fix first", *[f"{i}. {c['fix']}" for i, c in enumerate(fails[:6], 1)]]
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--user", required=True)
    ap.add_argument("--repos", default="", help="comma-separated pinned repo names")
    ap.add_argument("--market")
    ap.add_argument("--onet")
    ap.add_argument("--portfolio")
    ap.add_argument("--json")
    ap.add_argument("--md")
    a = ap.parse_args(argv)
    try:
        record = json.loads(pathlib.Path(a.portfolio).read_text()) if a.portfolio else None
        market = mk.load(a.market, a.onet or (record or {}).get("profile", {}).get("onet_code"))
        r = score(GitHub(), a.user, [x.strip() for x in a.repos.split(",") if x.strip()], market, record)
    except FetchError as e:
        print(f"STOPPED: {e}", file=sys.stderr)
        if re.search(r"\b(403|429)\b", str(e)):
            print("GitHub allows 60 keyless requests an hour per IP address, shared across a network. "
                  "Wait an hour, or set GITHUB_TOKEN (export GITHUB_TOKEN=$(gh auth token)) and rerun.", file=sys.stderr)
        return 3
    except (OSError, ValueError) as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    md = report_md(r)
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(r, indent=2))
    if a.md:
        pathlib.Path(a.md).write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
