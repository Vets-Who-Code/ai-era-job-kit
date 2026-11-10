"""O*NET database text files, pulled live from onetcenter.org (no key).

Files used (tab-separated, header row):
  Occupation Data.txt   O*NET-SOC Code | Title | Description
  Alternate Titles.txt  O*NET-SOC Code | Alternate Title | Short Title | Source(s)
  Technology Skills.txt O*NET-SOC Code | Example | Commodity Code | Commodity Title
                        | Hot Technology (Y/N) | In Demand (Y/N)
  Skills.txt            O*NET-SOC Code | Element ID | Element Name | Scale ID (IM/LV)
                        | Data Value | ...
"""

from __future__ import annotations

import csv
import io
import os
import re
import urllib.parse

from .net import FetchError, fetch

BASE = "https://www.onetcenter.org"
DB_PAGE = f"{BASE}/database.html"
ONLINE_SUMMARY = "https://www.onetonline.org/link/summary/{code}"


def latest_version() -> str:
    """Return the newest text-format release tag, e.g. '30_2'.

    Override with ONET_DB_VERSION=30_2 if the release page layout changes.
    """
    forced = os.environ.get("ONET_DB_VERSION")
    if forced:
        return forced.replace(".", "_")
    html = fetch(DB_PAGE)
    found = re.findall(r"db_(\d+)_(\d+)_text", html)
    if not found:
        raise FetchError(
            "Could not find an O*NET text release on the database page. "
            "Set ONET_DB_VERSION (for example 30_2) and rerun.")
    major, minor = max((int(a), int(b)) for a, b in found)
    return f"{major}_{minor}"


def _file_url(version: str, name: str) -> str:
    return f"{BASE}/dl_files/database/db_{version}_text/{urllib.parse.quote(name)}"


def read_table(version: str, name: str) -> list[dict]:
    text = fetch(_file_url(version, name), timeout=90)
    return parse_tsv(text)


def parse_tsv(text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    return [{(k or "").strip(): (v or "").strip() for k, v in row.items()} for row in reader]


def _col(row: dict, *candidates: str) -> str:
    """Header names drift a little between releases; match loosely."""
    lowered = {k.lower(): v for k, v in row.items()}
    for c in candidates:
        if c.lower() in lowered:
            return lowered[c.lower()]
    return ""


class Onet:
    """Lazy loader so one run fetches each file at most once."""

    def __init__(self, version: str | None = None):
        self.version = version or latest_version()
        self._cache: dict[str, list[dict]] = {}

    def _t(self, name: str) -> list[dict]:
        if name not in self._cache:
            self._cache[name] = read_table(self.version, name)
        return self._cache[name]

    # -- occupations -------------------------------------------------------
    def search(self, query: str, limit: int = 8) -> list[dict]:
        """Rank occupations by title / alternate-title match to a role name."""
        q = [w for w in re.findall(r"[a-z0-9+#.]+", query.lower()) if len(w) > 1]
        if not q:
            return []
        scores: dict[str, float] = {}
        titles: dict[str, str] = {}
        for row in self._t("Occupation Data.txt"):
            code = _col(row, "O*NET-SOC Code")
            title = _col(row, "Title")
            titles[code] = title
            hay = title.lower()
            hits = sum(1 for w in q if w in hay)
            if hits:
                scores[code] = scores.get(code, 0) + 3 * hits / len(q)
        try:
            alts = self._t("Alternate Titles.txt")
        except FetchError:
            alts = []
        for row in alts:
            code = _col(row, "O*NET-SOC Code")
            hay = (_col(row, "Alternate Title") + " " + _col(row, "Short Title")).lower()
            hits = sum(1 for w in q if w in hay)
            if hits == len(q):
                scores[code] = scores.get(code, 0) + 1.5
            elif hits:
                scores[code] = scores.get(code, 0) + 0.25 * hits / len(q)
        ranked = sorted(scores.items(), key=lambda kv: -kv[1])[:limit]
        return [{"code": c, "title": titles.get(c, ""), "match": round(s, 2),
                 "url": ONLINE_SUMMARY.format(code=c)} for c, s in ranked]

    def title(self, code: str) -> str:
        for row in self._t("Occupation Data.txt"):
            if _col(row, "O*NET-SOC Code") == code:
                return _col(row, "Title")
        raise FetchError(f"O*NET code {code} not found in release {self.version}")

    # -- demand signals ----------------------------------------------------
    def technology_skills(self, code: str) -> list[dict]:
        out = []
        for row in self._t("Technology Skills.txt"):
            if _col(row, "O*NET-SOC Code") != code:
                continue
            out.append({
                "skill": _col(row, "Example"),
                "category": _col(row, "Commodity Title"),
                "hot": _col(row, "Hot Technology").upper() == "Y",
                "in_demand": _col(row, "In Demand").upper() == "Y",
            })
        if not out:
            raise FetchError(f"No O*NET Technology Skills rows for {code}")
        return out

    def skills_importance(self, code: str, top: int = 12) -> list[dict]:
        rows = []
        for row in self._t("Skills.txt"):
            if _col(row, "O*NET-SOC Code") == code and _col(row, "Scale ID") == "IM":
                try:
                    val = float(_col(row, "Data Value"))
                except ValueError:
                    continue
                rows.append({"skill": _col(row, "Element Name"), "importance": val})
        rows.sort(key=lambda r: -r["importance"])
        return rows[:top]
