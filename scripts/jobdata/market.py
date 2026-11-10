"""The lane's in-demand skills, shared by every scorer in the chain.

Step 1 (resume_score.py) pulls O*NET (and postings) live and saves the ranked skills in its JSON.
Steps 2 to 4 reuse that file with --market, so every surface is scored against the same target.
Without it they pull O*NET live themselves with --onet. Neither path ever falls back to remembered data.
"""

from __future__ import annotations

import json
import pathlib

from . import demand as dm
from . import lexicon
from . import onet as onet_mod


def load(market_json: str | None = None, onet_code: str | None = None, top: int = 25) -> dict:
    """Return {"skills": [(name, weight)], "vocab": {...}, "source": str, "onet_code": str|None}."""
    if market_json:
        r = json.loads(pathlib.Path(market_json).read_text())
        skills = [(k["skill"], float(k["weight"])) for k in r.get("skills", [])][:top]
        if not skills:
            raise ValueError(f"{market_json} has no skills list. Run resume_score.py first, or pass --onet.")
        vocab = lexicon.build_vocab([s for s, _ in skills if s not in lexicon.CURATED])
        return {"skills": skills, "vocab": vocab, "source": f"resume score ({market_json})",
                "onet_code": r.get("onet_code")}
    if not onet_code:
        raise ValueError("Give --market <resume-score.json> from step 1, or --onet <code> for a live O*NET pull.")
    on = onet_mod.Onet()
    rows = on.technology_skills(onet_code)  # raises FetchError if the live pull fails
    demand, vocab = dm.build_demand(rows, [], top=top)
    return {"skills": [(d.skill, d.weight) for d in demand], "vocab": vocab,
            "source": f"O*NET {on.version} live, {onet_code}", "onet_code": onet_code}


def coverage(text: str, market: dict, top: int = 10) -> tuple[float, list[str], list[str]]:
    """Weighted share of the top skills named in text. Returns (share 0-1, found, missing)."""
    found_all = lexicon.find_skills(text, market["vocab"])
    sk = market["skills"][:top]
    tot = sum(w for _, w in sk) or 1
    found = [s for s, _ in sk if s in found_all]
    missing = [s for s, _ in sk if s not in found_all]
    return sum(w for s, w in sk if s in found_all) / tot, found, missing


def check(section: str, name: str, ok: bool, detail: str = "", weight: float = 1, fix: str = "") -> dict:
    return {"section": section, "check": name, "pass": bool(ok), "detail": detail, "weight": weight,
            "fix": "" if ok else fix}


def weighted(checks: list[dict]) -> int:
    tot = sum(c["weight"] for c in checks) or 1
    return round(100 * sum(c["weight"] for c in checks if c["pass"]) / tot)
