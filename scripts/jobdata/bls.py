"""BLS data, pulled live with no key.

1. Employment Projections, Table 1.2 (occupational projections and worker
   characteristics): 10-year growth %, annual openings, median annual wage.
   https://www.bls.gov/emp/tables/occupational-projections-and-characteristics.htm
2. BLS Public Data API v1 (no registration; small daily quota) for OEWS
   national wages: https://api.bls.gov/publicAPI/v1/timeseries/data/<series>

O*NET codes look like 15-1252.00; BLS uses the 6-digit SOC 15-1252.
"""

from __future__ import annotations

import os
import re
from html.parser import HTMLParser

from .net import FetchError, fetch, fetch_json

EP_URL = os.environ.get(
    "BLS_EP_URL",
    "https://www.bls.gov/emp/tables/occupational-projections-and-characteristics.htm")
API_V1 = "https://api.bls.gov/publicAPI/v1/timeseries/data/{series}"


def soc6(onet_code: str) -> str:
    m = re.match(r"(\d{2}-\d{4})", onet_code)
    if not m:
        raise ValueError(f"Not an O*NET/SOC code: {onet_code}")
    return m.group(1)


class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._row is not None and self._cell is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def _num(s: str) -> float | None:
    s = s.replace(",", "").replace("$", "").strip()
    if s in ("", "—", "-", "(1)", "(2)") or s.startswith("("):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_projections(html: str) -> dict[str, dict]:
    """Return {soc6: {...}} from the Table 1.2 HTML."""
    p = _TableParser()
    p.feed(html)
    header: list[str] | None = None
    out: dict[str, dict] = {}
    for row in p.rows:
        joined = " ".join(row).lower()
        if header is None:
            if "code" in joined and "percent" in joined and "openings" in joined:
                header = [h.lower() for h in row]
            continue
        code = next((c for c in row if re.fullmatch(r"\d{2}-\d{4}", c)), None)
        if not code or len(row) < len(header) - 1:
            continue

        def pick(*keys):
            for i, h in enumerate(header):
                if all(k in h for k in keys) and i < len(row):
                    return row[i]
            return ""

        out[code] = {
            "soc": code,
            "title": row[0],
            "employment_base_thousands": _num(pick("employment", "20")),
            "growth_pct_10yr": _num(pick("change", "percent")),
            "annual_openings_thousands": _num(pick("openings")),
            "median_wage": _num(pick("median", "wage")),
            "education": pick("education"),
            "header": [h for h in header if "employment" in h][:2],
        }
    if not out:
        raise FetchError("BLS projections table parsed to zero rows; layout may have changed. "
                         "Set BLS_EP_URL to the current Table 1.2 page.")
    return out


class Bls:
    def __init__(self):
        self._proj: dict[str, dict] | None = None

    def projections(self, onet_code: str) -> dict:
        if self._proj is None:
            self._proj = parse_projections(fetch(EP_URL, timeout=60))
        code = soc6(onet_code)
        if code in self._proj:
            row = dict(self._proj[code])
        else:
            # Some O*NET detail codes roll up to a broader BLS code (e.g. 15-1299).
            broad = code[:6] + "0"
            row = dict(self._proj.get(broad) or {})
            if not row:
                raise FetchError(f"No BLS projection row for SOC {code}")
            row["note"] = f"Rolled up to broader SOC {broad}"
        row["source"] = EP_URL
        return row

    @staticmethod
    def oews_national_median(onet_code: str) -> dict:
        """OEWS annual median wage (datatype 13), national, all industries."""
        occ = soc6(onet_code).replace("-", "")
        series = f"OEUN0000000000000{occ}13"
        data = fetch_json(API_V1.format(series=series))
        if data.get("status") != "REQUEST_SUCCEEDED":
            raise FetchError(f"BLS API: {data.get('status')} {data.get('message')}")
        s = (data.get("Results", {}).get("series") or [{}])[0]
        pts = s.get("data") or []
        if not pts:
            raise FetchError(f"BLS API returned no data for {series}")
        latest = pts[0]
        return {"series": series, "year": latest.get("year"),
                "median_annual_wage": _num(latest.get("value", "")),
                "source": API_V1.format(series=series)}
