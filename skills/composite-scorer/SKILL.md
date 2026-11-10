---
name: composite-scorer
description: "Step 5 of the scoring chain. Combines the resume, LinkedIn, GitHub and portfolio scores into two scores, a machine read (ATS and AI screeners) and a human read (recruiter, hiring manager, engineers), plus a resume gate, with the points left on each surface and the sync check beside them. Use after steps 1 to 4, or when someone asks for their overall score, a scorecard, or which surface to fix first."
---

# Composite scorer: two scores and a gate (step 5 of 7)

`$KIT` is two folders up from this skill's base directory.

## Run it
`python3 $KIT/scripts/scorecard.py composite --resume resume-score.json --linkedin linkedin-score.json --github github-score.json --portfolio portfolio-score.json --sync sync.md --json composite.json --md composite.md`

## The two reads
| Read | Who | Resume | LinkedIn | GitHub | Portfolio | Why |
|---|---|---|---|---|---|---|
| Machine | ATS and AI screeners | 40 | 35 | 15 | 10 | They read text literally: titles, keywords, dates, structure, match to the posting. They can't judge a running app or a design. |
| Human | Recruiter, hiring manager, engineers | 20 | 15 | 30 | 35 | People skim for proof: a live demo, real impact, a clear story, recent commits. |

**Resume gate (default 70):** a resume score under 70, or a resume that fails the parse gate, is flagged whatever either total says. A weak resume means no human ever sees the GitHub or the portfolio.

- These weights and the gate are a VWC design judgment (Nov 6 2026), not research and not any employer's. Say so when you report them. Change them with `--machine-weights resume=40,linkedin=35,github=15,portfolio=10`, `--human-weights portfolio=35,github=30,resume=20,linkedin=15` and `--gate 70`.
- A surface not run is left out of both reads and the rest are reweighted; the report marks the scores partial.
- The sync check sits beside the scores, not inside them.
- Before either read, the resume is rescored with the GitHub and LinkedIn `skill_evidence`: a skill is proven only when a resume bullet with a number names it and recent GitHub work or LinkedIn shows it. So the resume score here can be higher than step 1's.

## Report
Lead with the gate: passed or flagged, and why. Then the machine read and the human read, and the one surface with the most points left. Then go to step 6 (`improvement-plan`).
