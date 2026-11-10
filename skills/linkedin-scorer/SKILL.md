---
name: linkedin-scorer
description: "Step 2 of the scoring chain. Scores a LinkedIn profile (pasted text or LinkedIn's Save to PDF) against the same lane as the resume and against the portfolio record: headline, location, Open to Work, skills coverage, Featured, About, Experience and resume consistency. Use when someone asks to score, fix or check their LinkedIn, write a headline or About, or get found by recruiters."
---

# LinkedIn scorer (step 2 of 7)

`$KIT` is two folders up from this skill's base directory. This skill never logs in to LinkedIn or scrapes it.

## Why LinkedIn is scored
- Recruiters search with filters (skills, job title, location, open to work) and LinkedIn standardizes titles and skills [vendor: LinkedIn, see `$KIT/references/sources.md`]. Each field is a filter you match or miss.
- LinkedIn is for evidence, not applying. Recruiters compare it to the resume, and a mismatch is a red flag [Jerome, Feb 3 2026]. Rankers read it alongside the resume (`$KIT/references/ats-research.md`).
- It mirrors the portfolio record. If something isn't in `portfolio.json`, add it there first.
- The JSON carries `skill_evidence`: lane skills shown in Experience, Projects or Featured (not the Skills list). Step 1 and the composite use it to confirm a resume skill as proven.

## Run it
1. Paste the profile into a copy of `$KIT/templates/linkedin-profile.txt` (or save the profile as PDF from LinkedIn: More, then Save to PDF; needs `pdftotext`).
   The PDF leaves out Featured and Open to Work and lists only the top skills, so those two checks are skipped and the report says so. For a full score, use the pasted template.
2. `python3 $KIT/scripts/linkedin_score.py --profile linkedin.txt --market resume-score.json --portfolio <repo>/portfolio.json --resume <file> --json linkedin-score.json --md linkedin-score.md`
   (No step 1 file? `--onet <code>` pulls O*NET live.)
3. Report the score and the top five fixes, highest weight first. The weights are a VWC rubric; LinkedIn publishes no ranking.

## What good looks like (the fixes point here)
| Field | Rule |
|---|---|
| Headline | Target role + stack + one differentiator, in the posting's words |
| Location | The metro you're targeting, same as the resume |
| Open to Work | The exact titles you apply to (recruiters only, if employed) |
| Skills | Only skills a portfolio artifact proves, named the market's way |
| Featured | Flagship case study, the live app, one piece of writing |
| About | Three first-person paragraphs: what you build and for whom; proof with numbers; what you want next |
| Experience | The resume's strongest bullets, same titles, orgs and dates |

## Jerome's playbook
- Apply elsewhere, follow up here: apply on the company's site, then follow up through a LinkedIn connection.
- Post evidence, not branding: each artifact becomes a few posts (the problem, a decision, a bug and fix, a result). Draft them; they publish.

## Never
Never invent metrics, endorsements or experience, and never post for them.
