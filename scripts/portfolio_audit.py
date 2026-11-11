#!/usr/bin/env python3
"""Portfolio score: step 4 of the scoring chain. Automated checks for a portfolio site.

Covers what a script can verify, grouped by the sections of the VWC Portfolio Checklist. The
`portfolio-scorer` skill adds the human-judgment checks (story, first impression, depth of each artifact).

  python3 portfolio_audit.py --url https://yourname.dev [--portfolio <repo>/portfolio.json] \\
      [--checklist checklist.json] --json portfolio-score.json

It reads the home page and up to five project or case-study pages it links to, as raw HTML. A site that
only draws its content with JavaScript has nothing in that HTML: the script says so, fails that one check
and leaves out the checks that need the text, rather than failing them all.
--portfolio checks the site against the master record: each deployed artifact is on the site and its live
link loads.
--checklist adds the judgment pass to the score. The portfolio-scorer skill writes it:
  [{"section": "First Impression", "item": "Says what you build in one screen", "pass": true,
    "quote": "<what you saw on the page>"}]
Every item needs a quote of what was seen, pass or miss. Without it the score is the automated pass only.

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
from jobdata import calibration as cal  # noqa: E402
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
        self.scripts = 0
        self._skip = 0  # inside <script> or <style>: code, not page text
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
        if tag in ("script", "style"):
            self._skip += 1
            if tag == "script":
                self.scripts += 1
                if a.get("type") == "application/ld+json":
                    self.jsonld += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif data.strip() and not self._skip:
            self.text_chunks.append(data.strip())


def check(section, name, ok, detail="", weight=1, fix=""):
    return {"section": section, "check": name, "pass": bool(ok), "detail": detail, "weight": weight,
            "fix": "" if ok else (fix or f"Portfolio: {name[0].lower() + name[1:]}.")}


MIN_WORDS = 40  # fewer words than this in the raw HTML, with scripts on the page, reads as client-rendered
PROJECT_LINK = re.compile(r"project|case|work|portfolio|artifact", re.I)  # the kit's own word for them is artifacts
MAX_PAGES = 5


def score(results: list[dict]) -> int:
    tot = sum(r["weight"] for r in results) or 1
    return cal.calibrate(100 * sum(r["weight"] for r in results if r["pass"]) / tot)


def _loads(url: str) -> bool:
    try:
        fetch(url, timeout=20, retries=1)
        return True
    except FetchError:
        return False


def audit_site(url: str, record: dict | None = None) -> tuple[list[dict], list[str]]:
    """Return (checks, notes)."""
    res, notes = [], []
    t0 = time.time()
    try:
        html = fetch(url, timeout=30, retries=2)
    except FetchError as e:
        return [check("First Impression", "Site loads", False, str(e), 5)], notes
    secs = time.time() - t0
    p = Page()
    p.feed(html)
    home = " ".join(p.text_chunks).lower()
    links = [l.lower() for l in p.links]
    host = urllib.parse.urlparse(url).netloc

    # Project and case-study pages on the same site: the deep-dive checks read them too
    inner, seen = [], {url.rstrip("/")}
    for href in p.links:
        full = urllib.parse.urljoin(url, href).split("#")[0]
        if urllib.parse.urlparse(full).netloc != host or full.rstrip("/") in seen or not PROJECT_LINK.search(href):
            continue
        seen.add(full.rstrip("/"))
        try:
            q = Page()
            q.feed(fetch(full, timeout=20, retries=1))
            inner.append(" ".join(q.text_chunks).lower())
            links += [l.lower() for l in q.links]
        except FetchError:
            notes.append(f"Couldn't load {full}")
        if len(seen) > MAX_PAGES:
            break
    text = " ".join([home] + inner)
    rendered = len(home.split()) >= MIN_WORDS or p.scripts == 0

    res += [
        check("First Impression", "Site loads over HTTPS", url.startswith("https://"), url, 3),
        check("First Impression", "Loads fast (HTML < 2s)", secs < 2, f"{secs:.2f}s", 2),
        check("First Impression", "Page title set", len(p.title.strip()) >= 5, p.title.strip()[:80], 2),
        check("First Impression", "Mobile viewport meta", "viewport" in p.meta, "", 2),
        check("First Impression", "Content is in the HTML, readable without JavaScript", rendered,
              f"{len(home.split())} words in the raw HTML", 3,
              "Portfolio: prerender or server-render the pages. Scripts, link previews and many crawlers read the raw HTML, and yours has almost no text in it."),
    ]
    if rendered:
        res += [
            check("First Impression", "One clear H1", p.h1 == 1, f"{p.h1} h1 tags", 1),
            check("First Impression", "States the role you do in the text",
                  bool(re.search(r"\b(engineer|developer|architect|scientist|designer)\b", home)), "", 3),
            check("Proof of Work", "Links to GitHub", any("github.com" in l for l in links), "", 3),
            check("Proof of Work", "Has project or case-study pages", len(seen) - 1 >= 2 or len(inner) >= 2,
                  f"{len(inner)} project pages read", 3),
            check("Proof of Work", "Mentions live demos or deployed apps",
                  bool(re.search(r"\blive (?:demo|site|app|link|version)\b|\bdemo\b|\bdeployed\b|\bin production\b", text)), "", 2),
            check("Artifact Deep Dives", "Mentions decisions, tradeoffs or results",
                  bool(re.search(r"\btrade-?offs?\b|\bdecisions?\b|\barchitecture\b|\bresults?\b|\breduced\b|\bincreased\b", text)), "", 2),
            check("Technical Credibility Signals", "Mentions tests, CI or evals",
                  bool(re.search(r"\b(?:tests?|tested|testing)\b|ci/cd|github actions|\bevals?\b|observability", text)), "", 2),
            check("Technical Credibility Signals", "All images have alt text",
                  p.imgs == 0 or p.imgs_alt == p.imgs, f"{p.imgs_alt}/{p.imgs}", 2),
            check("Authority & Social Proof", "Links to writing, talks or press",
                  any(re.search(r"blog|substack|medium|dev\.to|youtube|talk|podcast|writing|articles?|posts?\b|press|speaking|newsletter", l) for l in links), "", 2),
            check("Authority & Social Proof", "Testimonials or endorsements",
                  bool(re.search(r"testimonial|recommendation|endorse", text)), "", 1),
            check("Discoverability & Distribution", "Links to LinkedIn", any("linkedin.com" in l for l in links), "", 2),
            check("Discoverability & Distribution", "Resume link",
                  any(re.search(r"resume|\bcv\b|\.pdf", l) for l in links), "", 2),
            check("Discoverability & Distribution", "Contact path (email, form or contact page)",
                  any(l.startswith("mailto:") or re.search(r"(?:^|/)contact", l) for l in links) or p.forms > 0, "", 3),
        ]
    else:
        notes.append("The pages are drawn by JavaScript, so this script couldn't read their text or links. "
                     "The checks that need them were left out, not failed. The checklist pass covers them.")
    res += [
        check("Technical Credibility Signals", "Declares page language", bool(p.lang), p.lang, 1),
        check("Discoverability & Distribution", "Meta description", len(p.meta.get("description", "")) >= 50,
              p.meta.get("description", "")[:120], 2),
        check("Discoverability & Distribution", "Open Graph image for link previews", "og:image" in p.meta, "", 2),
        check("Discoverability & Distribution", "Structured data (JSON-LD Person)", p.jsonld > 0, "", 1),
        check("Discoverability & Distribution", "Not blocked from search",
              "noindex" not in p.meta.get("robots", "").lower(), p.meta.get("robots", ""), 3),
    ]
    for path, name in (("/robots.txt", "robots.txt present"), ("/sitemap.xml", "sitemap.xml present")):
        res.append(check("Discoverability & Distribution", name, _loads(f"https://{host}{path}"), "", 1))

    # The site against the master record: every deployed artifact is on it, and its live link loads
    for art in (record or {}).get("artifacts", []):
        if (art.get("depth") or 0) < 2:
            continue
        nm, live = art.get("name", "artifact"), (art.get("url") or "").rstrip("/")
        if rendered:
            names = {nm.lower(), nm.lower().replace("-", " "), nm.lower().replace("_", " ")}
            on_site = any(n in text for n in names) or (bool(live) and any(live.lower() in l for l in links))
            res.append(check("Proof of Work", f"{nm} is on the site", on_site, "", 2,
                             f"Portfolio: add {nm} from portfolio.json to the site, with its case study."))
        res.append(check("Proof of Work", f"{nm}: live link loads", bool(live) and _loads(live), live or "no url in portfolio.json", 2,
                         f"Portfolio: fix the live link for {nm}" + (f" ({live})." if live else ": add its url to portfolio.json.")))
    return res, notes


def checklist_checks(items: list[dict]) -> list[dict]:
    """The judgment pass, written by the portfolio-scorer skill. Evidence is a quote: no quote, no item."""
    out = []
    for i in items:
        if not (i.get("section") and i.get("item") and isinstance(i.get("pass"), bool) and (i.get("quote") or "").strip()):
            raise ValueError(f"checklist item needs section, item, pass (true or false) and a quote of what was seen: {i}")
        out.append(check(i["section"], i["item"], i["pass"], i["quote"][:160], 2, i.get("fix") or f"Portfolio: {i['item']}."))
    return out


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


def summarize(results: list[dict], notes: list[str] = (), judged: bool = False) -> str:
    sections: dict[str, list[dict]] = {}
    for r in results:
        sections.setdefault(r["section"], []).append(r)
    L = [f"# Portfolio score (step 4 of the chain{'' if judged else ', automated'}): {score(results)} / 100", "",
         "Automated checks plus the checklist pass." if judged else
         "Automated checks only. The portfolio-scorer skill adds the judgment checks: rerun with --checklist.", ""]
    L += [f"Note: {n}" for n in notes] + ([""] if notes else [])
    for s, items in sections.items():
        L += [f"## {s}"]
        L += [f"- [{'x' if i['pass'] else ' '}] {i['check']}" + (f" ({i['detail']})" if i["detail"] else "")
              for i in items]
        L.append("")
    fails = sorted((r for r in results if not r["pass"]), key=lambda r: -r["weight"])
    if fails:
        L += ["## Fix first (highest weight)", *[f"{i}. {r['check']}" for i, r in enumerate(fails[:5], 1)], ""]
    L.append(cal.NOTE)
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", required=True)
    ap.add_argument("--github")
    ap.add_argument("--portfolio", help="portfolio.json: check each deployed artifact is on the site and its live link loads")
    ap.add_argument("--checklist", help="the judgment pass as JSON (see the top of this file); adds it to the score")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    try:
        record = json.loads(pathlib.Path(a.portfolio).expanduser().read_text()) if a.portfolio else None
        judged = checklist_checks(json.loads(pathlib.Path(a.checklist).read_text())) if a.checklist else []
    except (OSError, ValueError) as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    results, notes = audit_site(a.url, record)
    if a.github:
        results += audit_github(a.github)
    results += judged
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps({"surface": "portfolio", "score": score(results), "calibration": cal.CALIBRATION, "url": a.url,
                                                    "checks": results, "notes": notes,
                                                    "judgment_pass": bool(judged)}, indent=2))
    print(summarize(results, notes, bool(judged)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
