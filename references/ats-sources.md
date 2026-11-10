# Sources for the Screen Grade and the four readers

Checked 2026-11-01 by opening each page. Quotes are short and exact. Recheck before teaching; vendor docs change.

## The ATS

| Claim | Source | What it says |
|---|---|---|
| Grades A to D | Workday, *Reference: Candidate Grades* (updated 2023-06-23) https://doc.workday.com/hiredscore/en-us/workday-hiredscore/recruiter-productivity-/reference--candidate-grades.html | A: "meets all basic (required) qualifications, most preferred qualifications, and has an average qualification match above a defined threshold." B: "meets all basic qualifications." C: "meets most but not all basic qualifications." D: "does not meet most basic qualifications." |
| No grade for unreadable files | Workday, *HiredScore Grades* (2023-06-23) https://doc.workday.com/hiredscore/en-us/workday-hiredscore/recruiter-productivity-/concept--hiredscore-grades.html | No grade when "Candidates submit a resume in an unsupported format", or with no resume. |
| One qualification at a time, with evidence | Workday release notes, 2026-08-05 https://doc.workday.com/hiredscore/en-us/workday-hiredscore/hiredscore-release-notes/2026/august/wednesday--5th-august.html | The LLM "evaluates each screenable qualification individually against the candidate's parsed resume", with "pointers to relevant sections". |
| That LLM grading is opt-in | Workday, *Concept: Fit & Gap* https://doc.workday.com/hiredscore/en-us/workday-hiredscore/recruiter-productivity-/concept--fit---gap.html | "Evaluates basic and preferred qualifications individually"; available "only for customers who opt in". |
| Match categories, no auto-reject | Greenhouse, *Talent Matching FAQ* (2026-10-05) https://support.greenhouse.io/hc/en-us/articles/41131886674075 | Criteria: "required skills, relevant experience, job titles, and (optionally) industry"; categories "Strong, Good, Partial, Limited"; "does not auto-reject or auto-advance any candidate." |
| Oracle AI rating | Oracle 25B, *Job Application AI Rating* https://docs.oracle.com/en/cloud/saas/readiness/hcm/25b/recr-25b/25B-recruiting-wn-f37003.htm and setup page https://docs.oracle.com/en/cloud/saas/talent-management/farqa/how-do-i-set-up-ai-rating-for-job-applications.html | Rates Education, Experience, Profile and Skill 0 to 5 against the requisition. Scoring on application creation is an option, off by default. |
| Knockout questions | Greenhouse, *Application rules overview* (2026-03-02) https://support.greenhouse.io/hc/en-us/articles/203105595-Application-Rules-Overview | Auto-Reject "uses custom application questions to screen and reject candidates"; Auto-Reject wins over Auto-Advance. |
| Knockout points (Workday) | Workday, *Questionnaires for Recruiting* (2025-05-02) https://doc.workday.com/admin-guide/en-us/human-capital-management/recruiting/questionnaires/wjl1557399495805.html | Points on questions "to eliminate ineligible candidates and advance high scoring candidates." |

## The law

| Claim | Source | What it says |
|---|---|---|
| Yearly bias audit, median scoring rate | NYC Rules 6 RCNY 5-300 to 5-303, https://codelibrary.amlegal.com/codes/newyorkcity/latest/NYCrules/0-0-0-138530 ; DCWP final rule (2023) | Scoring rate: share of a category scoring "above the sample's median score"; impact ratio = that rate over the highest category's. Results posted on the employer's careers site. |
| One-year audit window | DCWP FAQ (2023-06-29) https://www.nyc.gov/assets/dca/downloads/pdf/about/DCWP-AEDT-FAQ.pdf | An audit can be relied on "for one year from the date it was conducted." |
| Any screen is a selection procedure | 29 CFR 1607.16 https://www.ecfr.gov/current/title-29/subtitle-B/chapter-XIV/part-1607/subject-group-ECFR22f759c519c83cc/section-1607.16 | "Any measure, combination of measures, or procedure used as a basis for any employment decision." |
| Anti-discrimination law covers AI | EEOC, *What is the EEOC's role in AI?* (2024) https://www.eeoc.gov/sites/default/files/2024-04/20240429_What%20is%20the%20EEOCs%20role%20in%20AI.pdf | Laws "apply to the use of AI ... just as they apply to other employment practices." The EEOC's 2023 AI technical-assistance page is no longer online; don't cite it. |

## The AI screener

| Claim | Source | What it says |
|---|---|---|
| Transcript scored against a rubric | Greenhouse, *Voice AI Data Processing FAQ* (2026-08-28) https://support.greenhouse.io/hc/en-us/articles/55090273099803-Voice-AI-Data-Processing-FAQ | Compares the transcript "against rubric criteria pre-established by the recruiter"; "a written scoring rationale citing specific candidate responses"; recordings "not used to produce the Voice AI Score"; flags "patterns consistent with reading or scripting" outside the score. |
| No accent or tone scoring | Greenhouse Voice AI page https://www.greenhouse.com/product-features/greenhouse-voice-ai ; Eightfold candidate hub (2026-07-27) https://eightfold.ai/candidate-hub/ | "not influenced by accent, tone, fluency, pace, personality or confidence"; "accent, tone, and pauses ... and facial expressions are not evaluated." |

## The recruiter

| Claim | Source | Status |
|---|---|---|
| Recruiter filters include skills, title, location, open to work; titles and skills are standardized | LinkedIn, *Using Advanced AI-Assisted Search* (PDF) https://business.linkedin.com/content/dam/lem/business/en/hire/product-update/Using%20AI-Assisted_Search_Semantic%20Search.pdf | Confirmed |
| Open to Work "recruiters only" visibility; 100-skill limit | LinkedIn Help answers 67405 and a549047 | **Not verified**: LinkedIn Help blocks automated reading. Check by hand before teaching. |

## Resume format

Harvard Extension School, Mignone Center for Career Success, *Resumes and Cover Letters* (2024). Rules used: specific, active, fact-based language; no pronouns; no narrative style; no numbered sections; no references; don't start each line with a date; reverse chronological order. The guide forbids reproducing its verb list, so the kit doesn't.

