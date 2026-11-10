---
name: improvement-plan
description: "Step 6 of the scoring chain. Turns the two scores into the steps needed to improve each section, biggest gain first: every failed check's fix by weight, the resume's top lift skills, and the sync mismatches, each pointed at the skill that fixes it. Use after the composite score, or when someone asks what to fix first or how to raise their score."
---

# Improvement plan (step 6 of 7)

`$KIT` is two folders up from this skill's base directory.

## Run it
`python3 $KIT/scripts/scorecard.py plan --composite composite.json --md plan.md`

A flagged resume gate goes first, whatever the other gaps, because a weak resume means no human sees the rest. Then surfaces are ranked by points left (weight x the gap to 100), averaged over the machine read and the human read. Each lists its failed checks, highest weight first, with the fix the scorer wrote.

## Turn it into work (portfolio first, always)
1. **Fix at the source.** A missing skill, number or project goes into `portfolio.json` and `brag/entries` first. Then the surfaces are regenerated from it.
2. **Resume:** prove the top lift skills in Experience or Projects bullets with numbers. Step 7 (`resume-rebuilder`) does the rebuild.
3. **LinkedIn:** rewrite the fields the plan names (headline, skills, About, Featured, Experience), matching the record. See `linkedin-scorer`.
4. **GitHub:** pins, profile README, repo READMEs, hygiene. See `github-scorer`.
5. **Portfolio:** artifact pages, live links, the checklist sections that failed. See `portfolio-scorer`.
6. **Sync:** clear every mismatch so all four surfaces tell one story.
Give them the exact text or files to change. They publish and push.

## Rules
Never invent a number or a skill to close a gap. A skill they can't prove becomes something to build, not something to claim.
