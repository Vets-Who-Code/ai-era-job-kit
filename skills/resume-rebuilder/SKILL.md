---
name: resume-rebuilder
description: "Step 7 of the scoring chain. Rebuilds the resume to the VWC spec as a projection of the portfolio (portfolio.json and curated brag entries), ordered by the resume score's lift list, with [ask: ...] for anything missing; then lints it, runs the defend-every-line check, and rescores. Use when someone asks to write, rewrite, tailor, fix or split a resume, make one for a specific role, or after the improvement plan."
---

# Resume rebuilder (step 7 of 7)

`$KIT` is two folders up from this skill's base directory. The portfolio is the source of truth: `portfolio.json` plus the curated Brag Database in `brag/entries/`. The resume is a projection of it, one targeted version per kind of role. Most people need one or two.

## Run it
1. **Draft from the record:**
   `python3 $KIT/scripts/resume_rebuild.py --portfolio <repo>/portfolio.json --brag <repo>/brag/entries --market resume-score.json [--role "<title>"] --out ~/resumes/<name>-<role>-resume.txt --md rebuild.md`
   Bullets that prove high-lift skills go first. Missing facts come out as `[ask: ...]`. Lane skills with no evidence in the portfolio are listed as "prove it first" and never added.
2. **Fill every [ask: ...] with them**, one at a time. Never guess a number.
3. **Tighten each bullet:** strong verb, what they built or changed, the skill named exactly as the market names it, and a number. A bullet with a number that names the skill is proven (1.0) once a pinned repo pushed in the last year or LinkedIn Experience shows the same skill; otherwise it's applied (0.7). A Skills-list mention is listed (0.4).
4. **Lint against the spec:** `python3 $KIT/scripts/resume_rebuild.py --check <file>` (works on .pdf, .docx, .txt).
5. **Defend every line** (below). Cut anything they can't defend.
6. **Rescore:** `resume_score.py` for the lane and `screen_grade.py` for the posting, before and after. Then `sync_check.py` so the resume agrees with the portfolio, LinkedIn and GitHub. If a resume line isn't in the portfolio, add it there first or cut it.
7. Save as PDF in their resume folder, outside any git repo (the script refuses one), and check the PDF's extracted text reads cleanly.

## The spec
- Single column; standard headings Experience, Projects, Skills, Education; no tables, text boxes, icons or images. [HES; what breaks the parser, `$KIT/references/ats-research.md`]
- Email and phone as plain text in the top lines, never in a header or footer.
- No pronouns, no "Responsible for", no line that starts with a date, reverse chronological, no numbered sections, no references. [HES]
- Experience length as "5+" or "10+" only; never more than "10+". [VWC]
- Projects carry each artifact with its live link; they weigh most when work history is short.
- Add an industries-served line when they have domain experience; recruiters filter on it.
- Length follows evidence, going back about 10 years. Military service is translated into outcomes.
- No hidden text, no keyword blocks outside Skills, no title inflation.

## Defend every line
Every line is a potential interview question; each should hold up for about 90 seconds. For each bullet, skill and title ask: what exactly did you do, which artifact proves it, what decision did you make and why, what broke, what would you do differently. Grade each: **Defended** (clear answer and evidence; any number appears in it), **Thin** (clear answer, no evidence: add it to the portfolio or soften the line), **Cut** (can't explain it or trace the number). For lines they can't defend: remove, study until they can, or reframe at the level they worked. Build the story table and the story bank of 8 from `$KIT/templates/story-table.md`, and a Stack Defense Doc from `$KIT/templates/stack-defense.md` (for every skill: what is it, when would you use it, the tradeoffs, a common mistake). The `ai-interviewer` and `final-round-panel` agents press on the rebuilt resume.

## Jerome's playbook
- **Fracture, don't tailor:** one master record becomes a few role resumes. "Same experience. Different signal. All true."
- **Don't over-strip:** lead with the target role and keep the preferred skills the postings list.
- **Signal strength:** "Built production Python services handling 10K RPS" beats "Developed Python applications", which beats "Experience with Python", which beats a Skills-list entry.
- **Decode the posting first:** sort each skill into required, preferred or nice-to-have; 3+ mentions marks it critical; map each to evidence before writing.
- **STAR-L bullets:** Situation, Task, Action, Result, and what they learned.

## Never
Never invent employers, titles, dates, metrics or skills. Respect NDAs: describe restricted clients generically.
