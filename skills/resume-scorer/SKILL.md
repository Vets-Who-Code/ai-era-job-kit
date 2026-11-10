---
name: resume-scorer
description: "Step 1 of the scoring chain. Scores a resume the way an ATS and its AI ranker read it: the parse gate first, then every in-demand skill for the lane graded proven, applied, listed, stale or none against live O*NET data (plus saved postings), with BLS outlook beside it; then, for one posting, the A to D Screen Grade. Use when someone asks to score, grade or check a resume, asks \"will this get past the ATS\" or \"why am I not getting callbacks\", or starts the scoring chain."
---

# Resume scorer (step 1 of 7)

`$KIT` is two folders up from this skill's base directory. Every ATS claim here comes from `$KIT/references/ats-research.md`, which traces each one to Jerome's chats or a vendor document. Say nothing about how an ATS works that isn't on that page.

## How the screen works (teach it in this order)
1. **Knockouts** run first: work authorization, sponsorship, minimum years, location, required certifications. Most fast rejections are knockouts and parse failures, not an AI judging content. Answer them deliberately.
2. **Parsing** turns the file into fields. It is still the gate: test the file before tuning content. Tables, columns, text boxes, headers and footers, graphics, image PDFs and non-standard section names break it.
3. **Search and filter.** The ATS is a database. Recruiters filter on keywords, years, location and education. Matching varies by vendor, so mirror the posting's exact phrasing where it's honest. State experience as 5+ or 10+.
4. **AI ranking.** HiredScore grades A to D one qualification at a time; Greenhouse sorts Strong to Limited; Oracle rates 0 to 5. Weights are set per role and aren't public, so the kit invents none.
5. **A human** reads what made it through. Satisfy the machine first, then the human.
Rankers also read LinkedIn and GitHub alongside the resume (steps 2 and 3). Old tricks (white text, keyword blocks, title inflation) now get flagged.

## Run it
1. **Lane score** (live O*NET; never from memory):
   `python3 $KIT/scripts/resume_score.py --resume <file> --onet <code> [--postings <dir>] --json resume-score.json --md resume-score.md`
   Find the code with `--role "<job title>"`. If the O*NET or BLS pull fails, the script stops (exit 3). Say so; don't fill in numbers.
   The score counts the best 10 of the lane's skills, weighted by demand (`--need`), so 100 means the ten most-wanted are proven, not every skill the occupation uses. [VWC]
2. **If the parse gate fails, stop there.** No score until the format is fixed: that's what the screener does. A missing email or phone doesn't block the score; it's listed as a fix.
3. **Screen Grade for one posting** (every application):
   `python3 $KIT/scripts/screen_grade.py split --greenhouse <board> --job <id> --out quals.json` (or `--lever`, `--ashby`, `--posting file.txt`)
   Grade each basic (B1...) and preferred (P1...) qualification in `grades.json`: Met needs an exact resume quote and its section; no quote, no Met; React doesn't prove Vue. Then
   `python3 $KIT/scripts/screen_grade.py grade --resume <file> --quals quals.json --grades grades.json --portfolio <repo>/portfolio.json --md screen.md`
   A = every basic plus more than half of preferred (read it as "A or B"; the threshold isn't published), B = every basic, C = most basic, D = half or fewer.
   Add `--out screen.json` so step 5 can report the grade. The script also refuses a quote that names none of the skills the qualification asks for.
4. **Check the grading** (METHOD rule 5): have the `ats-screener` agent grade the same `quals.json` into its own `grades-2.json`, then `python3 $KIT/scripts/screen_grade.py agree --quals quals.json --grades grades.json grades-2.json`. Under 90% or a different letter: reread the rule for each qualification they differ on and regrade.

## Report (five items max)
- The score and the grade ("62 / 100; B on this posting: 4 of 4 basic, 1 of 3 preferred").
- The top lift skills: each one's grade now and the points gained by proving it. Proven takes two things: a resume bullet with a number (a quantity, not the 3 in S3) that names the skill, and the same skill in a pinned repo pushed in the last year or in LinkedIn Experience, Projects or Featured. AI screeners read GitHub and LinkedIn too (`$KIT/references/ats-research.md`). Until steps 2 and 3 run, no skill is proven; pass their JSON with `--github` and `--linkedin`, or let the composite apply it.
- Not Met qualifications the portfolio already proves.
- Parse and format fixes, then chronology flags to be ready to explain (gaps, short roles).
- Hand `resume-score.json` to steps 2 to 4 with `--market`, so every surface is scored against the same target.

## Never
- Never add hidden text or keyword blocks, and never claim a skill they can't defend in a final round.
- Never call a score a hiring prediction. It mirrors documented screeners; employers configure their own.
- Never keep a resume inside a git repo; the scripts refuse.
