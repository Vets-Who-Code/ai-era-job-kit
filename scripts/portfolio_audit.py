#!/usr/bin/env python3
"""Portfolio score: step 4 of the scoring chain. Automated checks for a portfolio site.

Covers what a script can verify, grouped by the sections of the VWC Portfolio Checklist. The
`portfolio-scorer` skill adds the human-judgment checks (story, first impression, depth of each artifact).

  python3 portfolio_audit.py --url https://yourname.dev --json portfolio-score.json

GitHub is scored on its own in step 3 (github_score.py). --github still adds the old pinned-repo checks
through the GitHub CLI (`gh auth login`), but leave it off when you run the composite, or GitHub counts twice.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
from html.parser import HTMLParser

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from jobdata.net import FetchError, fetch  # noqa: E402


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self._in_title = False
        self.meta: dict[str, str] = {}
        self.links: list[str] = []
        self.imgs = 0
        self.imgs_alt = 0
        self.h1 = 0
        self.lang = ""
        self.jsonld = 0
        self.forms = 0
        self._in_jsonld = False
        self.text_chunks: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "html":
            self.lang = a.get("lang", "")
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = (a.get("name") or a.get("property") or "").lower()
            if key:
                self.meta[key] = a.get("content", "")
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])
        elif tag == "img":
            self.imgs += 1
            if a.get("alt", "").strip():
                self.imgs_alt += 1
        elif tag == "h1":
            self.h1 += 1
        elif tag == "form":
            self.forms += 1
        elif tag == "script" and a.get("type") == "application/ld+json":
            self.jsonld += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif data.strip():
            self.text_chunks.append(data.strip())


def check(section, name, ok, detail="", weight=1):
    return {"section": section, "check": name, "pass": bool(ok), "detail": detail, "weight": weight,
            "fix": "" if ok else f"Portfolio: {name[0].lower() + name[1:]}."}


def score(results: list[dict]) -> int:
    tot = sum(r["weight"] for r in results) or 1
    return round(100 * sum(r["weight"] for r in results if r["pass"]) / tot)


def audit_site(url: str) -> list[dict]:
    res = []
    t0 = time.time()
    try:
        html = fetch(url, timeout=30, retries=2)
    except FetchError as e:
        return [check("First Impression", "Site loads", False, str(e), 5)]
    secs = time.time() - t0
    p = Page()
    p.feed(html)
    text = " ".join(p.text_chunks).lower()
    links = [l.lower() for l in p.links]
    host = urllib.parse.urlparse(url).netloc

    res += [
        check("First Impression", "Site loads over HTTPS", url.startswith("https://"), url, 3),
        check("First Impression", "Loads fast (HTML < 2s)", secs < 2, f"{secs:.2f}s", 2),
        check("First Impression", "Page title set", len(p.title.strip()) >= 5, p.title.strip()[:80], 2),
        check("First Impression", "One clear H1", p.h1 == 1, f"{p.h1} h1 tags", 1),
        check("First Impression", "Mobile viewport meta", "viewport" in p.meta, "", 2),
        check("First Impression", "States the role you do in the text",
              bool(re.search(r"\b(engineer|developer|architect|scientist|designer)\b", text)), "", 3),
        check("Proof of Work", "Links to GitHub", any("github.com" in l for l in links), "", 3),
        check("Proof of Work", "Has project or case-study pages",
              sum(1 for l in links if re.search(r"project|case|work|portfolio", l)) >= 2,
              "looks for links containing project/case/work", 3),
        check("Proof of Work", "Mentions live demos or deployed apps",
              bool(re.search(r"\b(live|demo|deployed|production)\b", text)), "", 2),
        check("Artifact Deep Dives", "Mentions decisions, tradeoffs or results",
              bool(re.search(r"tradeoff|trade-off|decision|architecture|result|reduced|increased|users", text)), "", 2),
        check("Technical Credibility Signals", "Mentions tests, CI or evals",
              bool(re.search(r"\btest|ci/cd|github actions|\bevals?\b|observability", text)), "", 2),
        check("Technical Credibility Signals", "All images have alt text",
              p.imgs == 0 or p.imgs_alt == p.imgs, f"{p.imgs_alt}/{p.imgs}", 2),
        check("Technical Credibility Signals", "Declares page language", bool(p.lang), p.lang, 1),
        check("Authority & Social Proof", "Links to writing, talks or press",
              any(re.search(r"blog|substack|medium|dev\.to|youtube|talk|podcast", l) for l in links), "", 2),
        check("Authority & Social Proof", "Testimonials or endorsements",
              bool(re.search(r"testimonial|said|recommend|worked with", text)), "", 1),
        check("Discoverability & Distribution", "Meta description", len(p.meta.get("description", "")) >= 50,
              p.meta.get("description", "")[:120], 2),
        check("Discoverability & Distribution", "Open Graph image for link previews", "og:image" in p.meta, "", 2),
        check("Discoverability & Distribution", "Links to LinkedIn", any("linkedin.com" in l for l in links), "", 2),
        check("Discoverability & Distribution", "Structured data (JSON-LD Person)", p.jsonld > 0, "", 1),
        check("Discoverability & Distribution", "Not blocked from search",
              "noindex" not in p.meta.get("robots", "").lower(), p.meta.get("robots", ""), 3),
        check("Discoverability & Distribution", "Resume link",
              any(re.search(r"resume|cv|\.pdf", l) for l in links), "", 2),
        check("Discoverability & Distribution", "Contact path (email or form)",
              any(l.startswith("mailto:") for l in links) or p.forms > 0, "", 3),
    ]
    for path, name in (("/robots.txt", "robots.txt present"), ("/sitemap.xml", "sitemap.xml present")):
        try:
            fetch(f"https://{host}{path}", timeout=15, retries=1)
            ok = True
        except FetchError:
            ok = False
        res.append(check("Discoverability & Distribution", name, ok, "", 1))
    return res


def gh_json(args: list[str]):
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return json.loads(r.stdout)


PINNED_Q = """query($login:String!){user(login:$login){bio websiteUrl
 pinnedItems(first:6,types:REPOSITORY){nodes{... on Repository{name url description homepageUrl
 pushedAt licenseInfo{spdxId} repositoryTopics(first:10){nodes{topic{name}}}
 readme: object(expression:"HEAD:README.md"){... on Blob{byteSize}}
 workflows: object(expression:"HEAD:.github/workflows"){... on Tree{entries{name}}}}}}}}"""


def audit_github(login: str) -> list[dict]:
    if not shutil.which("gh"):
        return [check("Proof of Work", "GitHub checks", False, "GitHub CLI not installed", 0)]
    try:
        d = gh_json(["api", "graphql", "-f", f"query={PINNED_Q}", "-f", f"login={login}"])["data"]["user"]
    except Exception as e:  # noqa: BLE001
        return [check("Proof of Work", "GitHub checks", False, f"gh error: {e}", 0)]
    pins = d["pinnedItems"]["nodes"]
    res = [check("Proof of Work", "Profile bio set", bool(d.get("bio")), d.get("bio") or "", 1),
           check("Proof of Work", "Profile links to portfolio", bool(d.get("websiteUrl")), d.get("websiteUrl") or "", 2),
           check("Proof of Work", "Pinned repos (manicured only, each with a live or video demo)", len(pins) >= 1, f"{len(pins)} pinned", 3)]
    for r in pins:
        n = r["name"]
        res += [
            check("Technical Credibility Signals", f"{n}: README", bool(r.get("readme")),
                  f"{(r.get('readme') or {}).get('byteSize', 0)} bytes", 2),
            check("Technical Credibility Signals", f"{n}: CI workflow", bool(r.get("workflows")), "", 2),
            check("Technical Credibility Signals", f"{n}: license", bool(r.get("licenseInfo")), "", 1),
            check("Proof of Work", f"{n}: description + live link",
                  bool(r.get("description")) and bool(r.get("homepageUrl")), r.get("homepageUrl") or "", 2),
            check("Maintenance", f"{n}: pushed in last 90 days",
                  (r.get("pushedAt") or "") >= time.strftime("%Y-%m-%d", time.gmtime(time.time() - 90 * 86400)),
                  (r.get("pushedAt") or "")[:10], 1),
        ]
    return res


def summarize(results: list[dict]) -> str:
    sections: dict[str, list[dict]] = {}
    for r in results:
        sections.setdefault(r["section"], []).append(r)
    tot = sum(r["weight"] for r in results) or 1
    got = sum(r["weight"] for r in results if r["pass"])
    L = [f"# Portfolio score (step 4 of the chain, automated): {round(100 * got / tot)} / 100", "",
         "Automated checks only. The portfolio-scorer skill adds the judgment checks.", ""]
    for s, items in sections.items():
        L += [f"## {s}"]
        L += [f"- [{'x' if i['pass'] else ' '}] {i['check']}" + (f" ({i['detail']})" if i["detail"] else "")
              for i in items]
        L.append("")
    fails = sorted((r for r in results if not r["pass"]), key=lambda r: -r["weight"])
    if fails:
        L += ["## Fix first (highest weight)", *[f"{i}. {r['check']}" for i, r in enumerate(fails[:5], 1)]]
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", required=True)
    ap.add_argument("--github")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    results = audit_site(a.url)
    if a.github:
        results += audit_github(a.github)
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps({"surface": "portfolio", "score": score(results), "url": a.url,
                                                    "checks": results}, indent=2))
    print(summarize(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
