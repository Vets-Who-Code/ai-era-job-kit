"""Job postings as the employer-side signal.

Two keyless sources:
  * A folder of postings you saved (.txt / .md / .html). This is the course
    default: bring 10+ real postings for the roles you're applying to.
  * Public job boards for companies you name:
        greenhouse:<board>   boards-api.greenhouse.io
        lever:<company>      api.lever.co
        ashby:<org>          api.ashbyhq.com
"""

from __future__ import annotations

import html
import pathlib
import re

from .net import FetchError, fetch_json

_TAG = re.compile(r"<[^>]+>")


def strip_html(s: str) -> str:
    return " ".join(html.unescape(_TAG.sub(" ", html.unescape(s or ""))).split())


def load_folder(path: str) -> list[dict]:
    p = pathlib.Path(path).expanduser()
    if not p.is_dir():
        raise FileNotFoundError(f"Postings folder not found: {p}")
    out = []
    for f in sorted(p.iterdir()):
        if f.suffix.lower() in (".txt", ".md", ".html", ".htm"):
            text = f.read_text(errors="replace")
            if f.suffix.lower() in (".html", ".htm"):
                text = strip_html(text)
            out.append({"source": f.name, "title": f.stem, "text": text})
    return out


def _matches(title: str, role_filter: str | None) -> bool:
    if not role_filter:
        return True
    words = [w for w in role_filter.lower().split() if len(w) > 2]
    return any(w in title.lower() for w in words)


def from_board(spec: str, role_filter: str | None = None, limit: int = 40) -> list[dict]:
    kind, _, name = spec.partition(":")
    kind, name = kind.strip().lower(), name.strip()
    if not name:
        raise ValueError(f"Board spec needs a name, e.g. greenhouse:acme (got {spec!r})")
    jobs: list[dict] = []
    if kind == "greenhouse":
        data = fetch_json(f"https://boards-api.greenhouse.io/v1/boards/{name}/jobs?content=true")
        for j in data.get("jobs", []):
            if _matches(j.get("title", ""), role_filter):
                jobs.append({"source": spec, "title": j.get("title", ""),
                             "url": j.get("absolute_url", ""), "text": strip_html(j.get("content", ""))})
    elif kind == "lever":
        data = fetch_json(f"https://api.lever.co/v0/postings/{name}?mode=json")
        for j in data if isinstance(data, list) else []:
            if _matches(j.get("text", ""), role_filter):
                body = j.get("descriptionPlain", "") + " " + " ".join(
                    strip_html(x.get("content", "")) for x in j.get("lists", []))
                jobs.append({"source": spec, "title": j.get("text", ""),
                             "url": j.get("hostedUrl", ""), "text": body})
    elif kind == "ashby":
        data = fetch_json(f"https://api.ashbyhq.com/posting-api/job-board/{name}?includeCompensation=true")
        for j in data.get("jobs", []):
            if _matches(j.get("title", ""), role_filter):
                jobs.append({"source": spec, "title": j.get("title", ""), "url": j.get("jobUrl", ""),
                             "text": j.get("descriptionPlain") or strip_html(j.get("descriptionHtml", ""))})
    else:
        raise ValueError(f"Unknown board type {kind!r}; use greenhouse:, lever: or ashby:")
    return jobs[:limit]


def gather(folder: str | None, boards: list[str], role_filter: str | None) -> tuple[list[dict], list[str]]:
    """Return (postings, warnings). Board failures warn; they don't stop the run."""
    postings: list[dict] = []
    warnings: list[str] = []
    if folder:
        postings.extend(load_folder(folder))
    for b in boards:
        try:
            postings.extend(from_board(b, role_filter))
        except (FetchError, ValueError) as e:
            warnings.append(str(e))
    return postings, warnings
