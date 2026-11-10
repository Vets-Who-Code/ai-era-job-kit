#!/usr/bin/env python3
"""Job-search funnel tracker: one CSV, conversion by source, postmortems, weekly report.

  python3 funnel.py init  --file funnel.csv
  python3 funnel.py add   --file funnel.csv --company Acme --role "AI Engineer" \\
                          --source referral --resume-version ai-v2 --artifact "rag-eval-harness" \\
                          --next-action "ping hiring manager on LinkedIn" --follow-up 2026-11-14
  python3 funnel.py next  --file funnel.csv --id 7 --action "send thank-you" --follow-up 2026-11-12
  python3 funnel.py move  --file funnel.csv --id 7 --stage final
  python3 funnel.py close --file funnel.csv --id 7 --status rejected
  python3 funnel.py postmortem --file funnel.csv --id 7 \\
                          --cause "couldn't defend the Kafka line" \\
                          --fix "Stack Defense Doc entry for Kafka; 90 seconds out loud" --layer defense
  python3 funnel.py due   --file funnel.csv              # follow-ups due today or earlier
  python3 funnel.py report --file funnel.csv [--since 2026-10-01] [--md report.md]

Tracker columns (deck M7): date, company, role, source, resume version, status, next action,
follow-up, notes. Sources: job-board (Dice, Indeed), cold (company site), referral, recruiter,
network, inbound. --channel still works as an alias for --source.
Stages (furthest reached): applied, screen, second, third, final, offer
Status: active, rejected, ghosted, withdrawn, offer, accepted
Postmortem layers: resume (no screens), interview (screens, no finals), defense (finals, no offers),
channel (where you apply).

Weekly loop: Friday Setup -> sync check -> funnel review -> one postmortem per loss -> reallocate.
72-hour rule [VWC]: a fix with no upward stage movement within 72 hours was opinion, not
tactical intelligence; try the next fix. It is a rule of thumb for keeping fixes moving, with no
outside data behind it, and employers often take longer than 72 hours to answer. Set
FUNNEL_MOMENTUM_HOURS to judge fixes over a longer window. Keep funnel.csv outside any git repository.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import pathlib
import sys

FIELDS = ["id", "date_applied", "company", "role", "channel", "stage", "stage_date", "status",
          "resume_version", "next_action", "follow_up", "artifact_shared", "url",
          "pm_date", "pm_stage", "pm_cause", "pm_fix", "pm_layer", "lesson", "notes"]
CHANNELS = ["job-board", "cold", "referral", "recruiter", "network", "inbound"]
STAGES = ["applied", "screen", "second", "third", "final", "offer"]
STATUSES = ["active", "rejected", "ghosted", "withdrawn", "offer", "accepted"]
LOSSES = {"rejected", "ghosted"}
LAYERS = {
    "resume": "Resume score, Screen Grade, shift channels (resume-scorer, screen_grade.py)",
    "interview": "Interview practice: mock screens, rerun your weakest answers (/mock-screen, ai-interviewer)",
    "defense": "Defend every line: Stack Defense Doc, story table (resume-rebuilder, final-round-panel)",
    "channel": "Reallocate effort toward the source that converts (this report, By source)",
}
MOMENTUM_HOURS = int(os.environ.get("FUNNEL_MOMENTUM_HOURS", "72"))  # [VWC] the 72-hour rule

# No benchmark rates: the report shows only the learner's own numbers.


def now() -> dt.datetime:
    return dt.datetime.now().replace(microsecond=0)


def today() -> str:
    return dt.date.today().isoformat()


def load(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        sys.exit(f"{path} not found. Run: funnel.py init --file {path}")
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:  # older trackers: carry the old lesson column into the postmortem cause
        if r.get("lesson") and not r.get("pm_cause"):
            r["pm_cause"] = r["lesson"]
    return rows


def save(path: pathlib.Path, rows: list[dict]) -> None:
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})
    tmp.replace(path)


def find(rows, rid):
    for r in rows:
        if r["id"] == str(rid):
            return r
    sys.exit(f"No row with id {rid}")


def reached(row: dict, stage: str) -> bool:
    return STAGES.index(row.get("stage") or "applied") >= STAGES.index(stage)


def pct(n, d):
    return f"{(n / d):.1%}" if d else "n/a"


def diagnose(n: int, screens: int, finals: int, offers: int) -> tuple[str, str] | None:
    """Find the break point (deck M7 'Fix that layer'). Returns (symptom, layer) or None."""
    if n >= 10 and screens == 0:
        return "No screens", "resume"
    if screens >= 3 and finals == 0:
        return "Screens, but no finals", "interview"
    if finals >= 2 and offers == 0:
        return "Finals, but no offers", "defense"
    return None


def momentum_checks(rows: list[dict], at: dt.datetime) -> list[str]:
    """72-hour rule: did anything move up a stage within 72 hours of each postmortem fix?"""
    out = []
    for pm in rows:
        if not (pm.get("pm_fix") and pm.get("pm_date")):
            continue
        try:
            start = dt.datetime.fromisoformat(pm["pm_date"])
        except ValueError:
            continue
        end = start + dt.timedelta(hours=MOMENTUM_HOURS)
        if at < end:
            continue  # window still open
        moved = any((r.get("stage") or "applied") != "applied" and r.get("stage_date")
                    and start.date().isoformat() <= r["stage_date"] <= end.date().isoformat()
                    for r in rows)
        verdict = "upward movement, keep it" if moved else "no upward movement: it was opinion, try the next fix"
        out.append(f"- {pm['company']} fix \"{pm['pm_fix']}\" ({pm.get('pm_layer') or 'no layer'}): {verdict}")
    return out[-5:]


def build_report(rows: list[dict], since: str | None, at: dt.datetime | None = None) -> str:
    at = at or now()
    if since:
        rows = [r for r in rows if r["date_applied"] >= since]
    n = len(rows)
    out = [f"# Funnel report ({at.date().isoformat()})", "",
           f"Applications: {n}" + (f" since {since}" if since else ""), ""]
    if not n:
        return "\n".join(out + ["No applications yet. Add one with `funnel.py add`."])
    out += ["## Stage conversion (all sources)", "| Stage | Reached | From applied |", "|---|---|---|"]
    for s in STAGES:
        k = sum(reached(r, s) for r in rows)
        out.append(f"| {s} | {k} | {pct(k, n)} |")
    offers = sum(reached(r, "offer") for r in rows)
    screens = sum(reached(r, "screen") for r in rows)
    finals = sum(reached(r, "final") for r in rows)
    out += ["", f"Offer rate per application: {pct(offers, n)} · Screen-to-offer: {pct(offers, screens)}", ""]
    out += ["## By source", "| Source | Apps | Screen | Final | Offer | Screen rate | Offer rate |",
            "|---|---|---|---|---|---|---|"]
    rates = {}
    for c in CHANNELS + sorted({r["channel"] for r in rows} - set(CHANNELS)):
        cr = [r for r in rows if r["channel"] == c]
        if not cr:
            continue
        s, o = sum(reached(r, "screen") for r in cr), sum(reached(r, "offer") for r in cr)
        rates[c] = (s / len(cr), len(cr))
        out.append(f"| {c} | {len(cr)} | {s} | {sum(reached(r, 'final') for r in cr)} | {o} | "
                   f"{pct(s, len(cr))} | {pct(o, len(cr))} |")
    versions = sorted({r.get("resume_version", "") for r in rows if r.get("resume_version")})
    if len(versions) > 1:
        out += ["", "## By resume version", "| Resume version | Apps | Screens | Offers |", "|---|---|---|---|"]
        for v in versions:
            vr = [r for r in rows if r.get("resume_version") == v]
            out.append(f"| {v} | {len(vr)} | {sum(reached(r, 'screen') for r in vr)} | "
                       f"{sum(reached(r, 'offer') for r in vr)} |")
    shared = [r for r in rows if r.get("artifact_shared")]
    if shared:
        s1 = sum(reached(r, "screen") for r in shared)
        noart = [r for r in rows if not r.get("artifact_shared")]
        s2 = sum(reached(r, "screen") for r in noart)
        out += ["", "## Portfolio effect",
                f"Screen rate when an artifact was shared: {pct(s1, len(shared))} vs without: {pct(s2, len(noart))}"]

    dx = diagnose(n, screens, finals, offers)
    out += ["", "## Break point"]
    out.append(f"{dx[0]} -> fix the **{dx[1]}** layer: {LAYERS[dx[1]]}" if dx
               else "No clear break point yet. Keep volume up and recheck next week.")

    week_ago = (at.date() - dt.timedelta(days=7)).isoformat()
    recent = [r for r in rows if r["date_applied"] >= week_ago]
    stale_cut = (at.date() - dt.timedelta(days=21)).isoformat()
    stale = [r for r in rows if r["status"] == "active" and (r["stage_date"] or r["date_applied"]) < stale_cut]
    due = [r for r in rows if r["status"] == "active" and r.get("follow_up") and r["follow_up"] <= at.date().isoformat()]
    out += ["", "## This week", f"- New applications: {len(recent)}",
            f"- Follow-ups due: {len(due)}",
            f"- Active with no movement in 21+ days (follow up or mark ghosted): {len(stale)}"]
    for r in due[:10]:
        out.append(f"  - #{r['id']} {r['company']} / {r['role']}: {r.get('next_action') or 'follow up'} (due {r['follow_up']})")

    losses = [r for r in rows if r["status"] in LOSSES]
    pms = [r for r in rows if r.get("pm_cause")]
    out += ["", "## Postmortems (blameless: one incident, one cause, one fix)",
            f"Losses: {len(losses)} · Postmortems written: {sum(1 for r in losses if r.get('pm_cause'))}"]
    for r in pms[-10:]:
        fix = f" -> fix: {r['pm_fix']}" if r.get("pm_fix") else ""
        layer = f" [{r['pm_layer']}]" if r.get("pm_layer") else ""
        out.append(f"- {r['company']} / {r['role']} (broke at {r.get('pm_stage') or r['stage']}): {r['pm_cause']}{fix}{layer}")
    mom = momentum_checks(rows, at)
    if mom:
        out += ["", f"## {MOMENTUM_HOURS}-hour rule", *mom,
                f"[VWC] rule of thumb, not data: replies often take longer than {MOMENTUM_HOURS} hours. "
                "Before dropping a fix, check that enough applications went out with it to tell."]

    # What to do next: one ordered stack, highest leverage first.
    nxt = []
    if dx:
        nxt.append(f"Fix the {dx[1]} layer first: {LAYERS[dx[1]]}.")
    missing_pm = [r for r in losses if not r.get("pm_cause")]
    if missing_pm:
        nxt.append(f"Write {len(missing_pm)} postmortem(s): `funnel.py postmortem --id {missing_pm[0]['id']} ...`.")
    if due:
        nxt.append(f"Clear {len(due)} follow-up(s) due today or earlier (`funnel.py due`).")
    sized = {c: v for c, v in rates.items() if v[1] >= 5}
    if len(sized) >= 2:
        best = max(sized, key=lambda c: sized[c][0])
        worst = min(sized, key=lambda c: sized[c][0])
        if sized[best][0] > sized[worst][0]:
            nxt.append(f"Reallocate: move effort from {worst} ({sized[worst][0]:.0%} screen rate) "
                       f"toward {best} ({sized[best][0]:.0%}).")
    if stale:
        nxt.append(f"Follow up on {len(stale)} stale applications, then mark the rest ghosted.")
    if nxt:
        out += ["", "## Next moves (in priority order)", *[f"{i}. {t}" for i, t in enumerate(nxt, 1)]]
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("init", "add", "next", "move", "close", "postmortem", "due", "report"):
        p = sub.add_parser(name)
        p.add_argument("--file", default="funnel.csv")
        if name == "add":
            p.add_argument("--company", required=True)
            p.add_argument("--role", required=True)
            p.add_argument("--source", "--channel", dest="channel", choices=CHANNELS, required=True)
            p.add_argument("--date", default=today())
            p.add_argument("--resume-version", default="")
            p.add_argument("--next-action", default="")
            p.add_argument("--follow-up", default="", help="YYYY-MM-DD")
            p.add_argument("--artifact", default="", help="portfolio artifact you shared")
            p.add_argument("--url", default="")
            p.add_argument("--notes", default="")
        if name == "next":
            p.add_argument("--id", required=True)
            p.add_argument("--action", required=True)
            p.add_argument("--follow-up", default="", help="YYYY-MM-DD")
        if name == "move":
            p.add_argument("--id", required=True)
            p.add_argument("--stage", choices=STAGES, required=True)
        if name == "close":
            p.add_argument("--id", required=True)
            p.add_argument("--status", choices=STATUSES, required=True)
            p.add_argument("--lesson", default="", help="shortcut for a postmortem cause")
        if name == "postmortem":
            p.add_argument("--id", required=True)
            p.add_argument("--stage", choices=STAGES, help="where it broke (default: furthest stage reached)")
            p.add_argument("--cause", required=True, help="the one cause you can act on")
            p.add_argument("--fix", required=True, help="the one change you'll make")
            p.add_argument("--layer", choices=sorted(LAYERS), required=True, help="the layer the fix touches")
        if name == "report":
            p.add_argument("--since")
            p.add_argument("--md")
    a = ap.parse_args(argv)
    path = pathlib.Path(a.file)

    if a.cmd == "init":
        if path.exists():
            print(f"{path} already exists; left it alone.")
        else:
            save(path, [])
            print(f"Created {path}")
        return 0
    rows = load(path)
    if a.cmd == "add":
        nid = max((int(r["id"]) for r in rows), default=0) + 1
        rows.append({"id": nid, "date_applied": a.date, "company": a.company, "role": a.role,
                     "channel": a.channel, "stage": "applied", "stage_date": a.date, "status": "active",
                     "resume_version": a.resume_version, "next_action": a.next_action,
                     "follow_up": a.follow_up, "artifact_shared": a.artifact, "url": a.url, "notes": a.notes})
        save(path, rows)
        print(f"Added #{nid} {a.company} / {a.role}")
    elif a.cmd == "next":
        r = find(rows, a.id)
        r["next_action"], r["follow_up"] = a.action, a.follow_up or r.get("follow_up", "")
        save(path, rows)
        print(f"#{a.id} next: {a.action}" + (f" (follow up {r['follow_up']})" if r["follow_up"] else ""))
    elif a.cmd == "move":
        r = find(rows, a.id)
        if STAGES.index(a.stage) < STAGES.index(r["stage"] or "applied"):
            sys.exit("Stages only move forward. Use close to end an application.")
        r["stage"], r["stage_date"] = a.stage, today()
        if a.stage == "offer":
            r["status"] = "offer"
        save(path, rows)
        print(f"#{a.id} -> {a.stage}")
    elif a.cmd == "close":
        r = find(rows, a.id)
        r["status"], r["stage_date"] = a.status, today()
        r["next_action"], r["follow_up"] = "", ""
        if a.lesson:
            r["pm_cause"] = r["lesson"] = a.lesson
        save(path, rows)
        print(f"#{a.id} closed as {a.status}")
        if a.status in LOSSES and not r.get("pm_fix"):
            print(f"Write the postmortem: funnel.py postmortem --file {a.file} --id {a.id} --cause ... --fix ... --layer ...")
    elif a.cmd == "postmortem":
        r = find(rows, a.id)
        r.update({"pm_date": now().isoformat(), "pm_stage": a.stage or r["stage"] or "applied",
                  "pm_cause": a.cause, "pm_fix": a.fix, "pm_layer": a.layer, "lesson": a.cause})
        save(path, rows)
        print(f"#{a.id} postmortem: broke at {r['pm_stage']} · cause: {a.cause} · fix ({a.layer}): {a.fix}")
        print(f"{MOMENTUM_HOURS}-hour rule: check the next report. No upward movement means try the next fix.")
    elif a.cmd == "due":
        d = [r for r in rows if r["status"] == "active" and r.get("follow_up") and r["follow_up"] <= today()]
        if not d:
            print("Nothing due.")
        for r in d:
            print(f"#{r['id']} {r['company']} / {r['role']}: {r.get('next_action') or 'follow up'} (due {r['follow_up']})")
    elif a.cmd == "report":
        md = build_report(rows, a.since)
        if a.md:
            pathlib.Path(a.md).write_text(md)
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
