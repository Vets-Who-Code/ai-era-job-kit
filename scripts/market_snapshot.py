#!/usr/bin/env python3
"""Market snapshot: live O*NET + BLS data for the roles your experience already
points to, plus which skills real postings for those roles ask for. Use it to
see where you stand today and what your portfolio should prove. It informs
the build; it doesn't ask you to narrow down to one specialty.

Examples
  python3 market_snapshot.py --roles "software developer" "web developer"
  python3 market_snapshot.py --codes 15-1252.00 15-1254.00 --postings ./postings --out market-snapshot
  python3 market_snapshot.py --find "ai engineer"      # just list matching O*NET occupations
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from jobdata import bls as bls_mod, demand as dm, onet as onet_mod, postings as post_mod  # noqa: E402
from jobdata.net import FetchError  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--roles", nargs="*", default=[])
    ap.add_argument("--codes", nargs="*", default=[])
    ap.add_argument("--find", help="search O*NET occupations by name and exit")
    ap.add_argument("--postings")
    ap.add_argument("--boards", nargs="*", default=[])
    ap.add_argument("--role-filter")
    ap.add_argument("--out")
    a = ap.parse_args(argv)

    try:
        on = onet_mod.Onet()
        if a.find:
            for m in on.search(a.find):
                print(f"{m['code']}  {m['title']}  (match {m['match']})  {m['url']}")
            return 0
        codes = list(a.codes)
        for r in a.roles:
            hit = on.search(r, limit=1)
            if hit:
                codes.append(hit[0]["code"])
            else:
                print(f"warning: no O*NET match for {r!r}", file=sys.stderr)
        if not codes:
            ap.error("give --roles or --codes")
        posts, warn = post_mod.gather(a.postings, a.boards, a.role_filter)
        b = bls_mod.Bls()
        roles = []
        for c in dict.fromkeys(codes):
            tech = on.technology_skills(c)
            demand, _ = dm.build_demand(tech, posts, top=12)
            o = b.projections(c)
            roles.append({
                "onet_code": c, "title": on.title(c),
                "growth_pct_10yr": o.get("growth_pct_10yr"),
                "annual_openings_thousands": o.get("annual_openings_thousands"),
                "median_wage": o.get("median_wage"),
                "hot_tech_count": sum(1 for t in tech if t["hot"]),
                "top_skills": [d.skill for d in demand],
                "onet_url": onet_mod.ONLINE_SUMMARY.format(code=c),
            })
    except FetchError as e:
        print(f"STOPPED: {e}", file=sys.stderr)
        return 3

    lines = ["# Market snapshot (live O*NET + BLS)", "",
             f"O*NET release {on.version.replace('_', '.')} · {len(posts)} postings", "",
             "| Role | Code | 10-yr growth | Openings / yr (k) | Median wage | Top skills |",
             "|---|---|---|---|---|---|"]
    for L in sorted(roles, key=lambda x: -(x["annual_openings_thousands"] or 0)):
        wage = f"${L['median_wage']:,.0f}" if L["median_wage"] else "n/a"
        lines.append(f"| {L['title']} | {L['onet_code']} | {L['growth_pct_10yr']}% | "
                     f"{L['annual_openings_thousands']} | {wage} | {', '.join(L['top_skills'][:8])} |")
    for w in warn:
        lines.append(f"\n- warning: {w}")
    md = "\n".join(lines)
    if a.out:
        pathlib.Path(a.out + ".json").write_text(json.dumps(roles, indent=2))
        pathlib.Path(a.out + ".md").write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
