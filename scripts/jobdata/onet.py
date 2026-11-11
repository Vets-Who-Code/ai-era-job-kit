"""O*NET database text files, pulled live from onetcenter.org (no key).

Files used, by the name they had through release 30.x (tab-separated text, header row):
  Occupation Data.txt   O*NET-SOC Code | Title | Description
  Alternate Titles.txt  O*NET-SOC Code | Alternate Title | Short Title | Source(s)
  Technology Skills.txt O*NET-SOC Code | Example | Commodity Code | Commodity Title
                        | Hot Technology (Y/N) | In Demand (Y/N)
  Skills.txt            O*NET-SOC Code | Element ID | Element Name | Scale ID (IM/LV)
                        | Data Value | ...

Release 31.0 dropped the text format and renamed files and columns. From 31.0 the same tables are
CSV: occupation_data.csv, job_titles.csv (Job Title), software_skills.csv (Workplace Example,
Element Name), essential_skills.csv. Both layouts are read; the rest of the kit sees one shape.
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


CSV_FROM = 31  # first release without the text format
CSV_NAMES = {
    "Occupation Data.txt": "occupation_data.csv",
    "Alternate Titles.txt": "job_titles.csv",
    "Technology Skills.txt": "software_skills.csv",
    "Skills.txt": "essential_skills.csv",
}


def latest_version() -> str:
    """Return the newest release tag on the database page, e.g. '31_0'.

    Override with ONET_DB_VERSION=31_0 if the release page layout changes.
    """
    forced = os.environ.get("ONET_DB_VERSION")
    if forced:
        return forced.replace(".", "_")
    html = fetch(DB_PAGE)
    found = re.findall(r"db_(\d+)_(\d+)_(?:text|csv)", html)
    if not found:
        raise FetchError(
            "Could not find an O*NET release on the database page. "
            "Set ONET_DB_VERSION (for example 31_0) and rerun.")
    major, minor = max((int(a), int(b)) for a, b in found)
    return f"{major}_{minor}"


def _is_csv(version: str) -> bool:
    m = re.match(r"(\d+)", version)
    return bool(m) and int(m.group(1)) >= CSV_FROM


def _file_url(version: str, name: str) -> str:
    if _is_csv(version):
        return f"{BASE}/dl_files/database/db_{version}_csv/{CSV_NAMES[name]}"
    return f"{BASE}/dl_files/database/db_{version}_text/{urllib.parse.quote(name)}"


def read_table(version: str, name: str) -> list[dict]:
    text = fetch(_file_url(version, name), timeout=90)
    return parse_tsv(text, delimiter="," if _is_csv(version) else "\t")


def parse_tsv(text: str, delimiter: str = "\t") -> list[dict]:
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")), delimiter=delimiter)
    return [{(k or "").strip(): (v or "").strip() for k, v in row.items()} for row in reader]


def _word_in(word: str, hay: str) -> bool:
    """True if a word in hay starts with `word` ("engineer" finds "engineers"). Words of one or two letters
    must match whole, so "ai" doesn't find "aircraft" or the middle of "maintenance"."""
    tail = r"(?![a-z0-9])" if len(word) <= 2 else ""
    return re.search(r"(?<![a-z0-9])" + re.escape(word) + tail, hay) is not None


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
        """Rank occupations by title / alternate-title match to a role name.

        An occupation that lists the role by name ("AI Engineer", "Back End Engineer") outranks any that only
        shares a word with it: "engineer" alone would send every engineering role to Civil Engineers."""
        q = [w for w in re.findall(r"[a-z0-9+#.]+", query.lower()) if len(w) > 1]
        if not q:
            return []
        squash = lambda t: re.sub(r"[^a-z0-9+#.]", "", t.lower())  # "Back-End" = "backend" = "back end"
        nq = squash(query)
        scores: dict[str, float] = {}
        partial: dict[str, float] = {}
        titles: dict[str, str] = {}
        for row in self._t("Occupation Data.txt"):
            code = _col(row, "O*NET-SOC Code")
            title = _col(row, "Title")
            titles[code] = title
            hay = title.lower()
            hits = sum(1 for w in q if _word_in(w, hay))
            if hits:
                scores[code] = scores.get(code, 0) + 3 * hits / len(q)
            if squash(title) in (nq, nq + "s"):
                scores[code] = scores.get(code, 0) + 10
        try:
            alts = self._t("Alternate Titles.txt")
        except FetchError:
            alts = []
        named: set[str] = set()
        for row in alts:
            code = _col(row, "O*NET-SOC Code")
            alt, short = _col(row, "Alternate Title", "Job Title"), _col(row, "Short Title")
            hay = (alt + " " + short).lower()
            hits = sum(1 for w in q if _word_in(w, hay))
            # "AI Engineer (Artificial Intelligence Engineer)": either name is the role
            if code not in named and nq in {squash(x) for x in [short, *re.split(r"[()]", alt)]}:
                named.add(code)
                scores[code] = scores.get(code, 0) + 10
            if hits == len(q) or nq in squash(alt):
                scores[code] = scores.get(code, 0) + 1.5
            elif hits:  # a shared word is weak: count the best one once, not once per alternate title
                partial[code] = max(partial.get(code, 0), 0.25 * hits / len(q))
        for code, v in partial.items():
            scores[code] = scores.get(code, 0) + v
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
                "skill": _col(row, "Example", "Workplace Example"),
                "category": _col(row, "Commodity Title", "Element Name"),
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
