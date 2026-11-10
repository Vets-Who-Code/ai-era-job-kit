"""Rank the skills employers ask for in one occupation: live O*NET flags plus job postings.

Used by resume_score.py (step 1 of the scoring chain, via jobdata.market for steps 2 to 4) and by
market_snapshot.py for the "Top skills" column.

Ranking (the market prevails, the same rule as hashflag's resume-market-scorer):
    with postings     rank by share of postings that mention the skill; O*NET flags break ties
    without postings  rank by O*NET flags (In Demand, Hot Technology), and say so
Skills tied at the cut-off all stay in: `top` is a floor, not an alphabetical cut.
"""


from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field

from . import lexicon


@dataclass
class DemandSkill:
    skill: str
    weight: float
    onet_hot: bool = False
    onet_in_demand: bool = False
    posting_share: float = 0.0
    grade: int = 0
    artifacts: list = field(default_factory=list)


def build_demand(onet_rows: list[dict], postings: list[dict], top: int = 25):
    """Return (demand list, vocab)."""
    onet_flags: dict[str, dict] = {}
    extra_onet_names = []
    for r in onet_rows:
        hits = lexicon.find_skills(r["skill"], lexicon.CURATED)
        targets = hits or {r["skill"]}
        if not hits:
            extra_onet_names.append(r["skill"])
        for t in targets:
            f = onet_flags.setdefault(t, {"hot": False, "in_demand": False})
            f["hot"] |= r["hot"]
            f["in_demand"] |= r["in_demand"]
    vocab = lexicon.build_vocab(extra_onet_names)

    n = len(postings)
    counts = lexicon.count_in_docs([p["text"] for p in postings], vocab) if n else {}

    out: list[DemandSkill] = []
    for skill in vocab:
        f = onet_flags.get(skill, {"hot": False, "in_demand": False})
        onet = (int(f["in_demand"]) + int(f["hot"])) / 2
        share = counts.get(skill, 0) / n if n else 0.0
        w = share + onet / 100 if n else onet  # O*NET only breaks ties when postings exist
        if w > 0:
            out.append(DemandSkill(skill, round(w, 4), f["hot"], f["in_demand"], round(share, 3)))
    out.sort(key=lambda d: (-d.weight, d.skill))
    if len(out) > top:  # keep every skill tied with the last one in, so the alphabet never decides the cut
        edge = out[top - 1].weight
        top = max(top, sum(1 for d in out if d.weight >= edge))
        if not postings:  # O*NET flags give only two weights: don't let a tie pull in the whole long tail
            top = min(top, sum(1 for d in out if d.weight >= out[0].weight)) if out[0].weight > edge else top
    return out[:top], vocab


