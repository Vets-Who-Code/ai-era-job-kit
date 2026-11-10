# How the ATS works: every claim and where it came from

Rebuilt 2026-11-06 from Jerome's own chats and the vendor documents they led to. Each claim names its source: a chat (title, date) or a document. Vendor and law documents are listed with links in `references/ats-sources.md`. A claim that only a chat supports is marked **chat only**: it is Jerome's research or teaching, not something a vendor publishes. The course and the scorers use nothing that isn't on this page.

## The pipeline, in order

Screening is a stack of layers, and a candidate has to clear each one in order ("Master.dev support for veteran developers", Sept 17 2026).

| # | Layer | What happens | Source |
|---|---|---|---|
| 1 | Knockout questions | Application questions screen people out first: work authorization, sponsorship, minimum years, location or relocation, required certifications. Most fast rejections come from knockouts and parse failures, not from an AI judging content. Answer them deliberately. | Sept 17 2026 chat; "How ATS systems evaluate candidates beyond keywords", Jan 11 2026. Greenhouse auto-reject rules win over auto-advance; Workday questionnaires score answers "to eliminate ineligible candidates" (ats-sources.md) |
| 2 | Parsing | The file becomes structured fields: contact info, work history, education, skills, dates. Parsing is still the gate; test the file in a parser before tuning any content. | "Comprehensive course outline development", Feb 3 2026 (Lesson 2.1); Jan 11 2026; "Job course outline", Oct 7 2026 (Block A); Sept 17 2026. Workday HiredScore gives no grade to "a resume in an unsupported format" (ats-sources.md) |
| 3 | Search and filter | The ATS is a database with search and filter functions. Recruiters filter on keywords, years of experience, location and education, and results come back ranked by match. | Feb 3 2026 (Lesson 2.1: "ATS are databases with search and filter functions... predictable") |
| 4 | AI ranking | AI ranks applicants, and the bottom of the rank may never reach a human. Workday HiredScore grades A to D against the posting's basic and preferred qualifications, one qualification at a time, pointing to the resume section. Greenhouse Talent Matching sorts into Strong, Good, Partial, Limited on required skills, relevant experience, job titles and (optionally) industry, and doesn't auto-reject. Oracle can rate Education, Experience, Profile and Skill 0 to 5. | Sept 17 2026; "Resume skills market alignment", Oct 14 2026 (Jerome: "we know that AI is playing a huge part of this"). Workday, Greenhouse and Oracle docs (ats-sources.md) |
| 5 | A human | A recruiter or hiring manager reads what made it through. | Feb 3 2026 ("Top N% reviewed by human") |

## What breaks the parser

| Breaks it | What happens | Source |
|---|---|---|
| Tables and side-by-side columns | Content is read out of order | Feb 3 2026; Jan 11 2026; Oct 7 2026 |
| Text boxes | Content lands in the wrong field or is lost | Jan 11 2026; Oct 7 2026 |
| Headers and footers holding key info | Often skipped | Feb 3 2026; Jan 11 2026; Oct 7 2026 |
| Graphics and icons | Ignored | Feb 3 2026 |
| Non-standard section names ("Selected AI Projects", "Teaching & Thought Leadership") | Misclassified or missed; use Experience, Projects, Skills, Education | Feb 3 2026; "Updating work experience with recent projects", Feb 4 2026 |
| A PDF made from an image | Nothing is extracted | Feb 3 2026 |
| Unusual fonts | Characters aren't recognized | Feb 3 2026 (chat only) |
| Special characters (arrows, tildes, bullet separators in the contact line) | Some parsers choke on them | Feb 4 2026 (chat only) |

**Parse test:** extract the plain text. If name, titles, companies and dates come out in order, a parser can read it. No vendor publishes its parser, so this is a testable proxy ("Resume skills market alignment", Oct 14 2026).

## How matching works

- **Keywords still count, and matching varies by vendor.** "Managed projects" matches "project management" in some systems and not others. Mirror the posting's exact phrasing where it's honest (Sept 17 2026).
- **Semantic matching through skills taxonomies** relates terms that aren't spelled the same (Jan 11 2026; Oct 7 2026). The kit uses O*NET names and a curated alias list.
- **Evidence over lists.** Every important skill should appear in at least one work bullet, project, certification or portfolio proof point (Sept 17 2026). HiredScore points to the section that proves each qualification (Workday, ats-sources.md).
- **Years:** five to ten years is the sweet spot for ATS searches; state experience as 5+ or 10+ (Sept 17 2026 transcript, filed in `jerome-chat-archive.md`).

## What the score weighs

- **Weights are set per role** (experience, recency, location, industry), so the same resume scores differently for two similar jobs (Oct 7 2026 Block A; Jan 11 2026).
- **Each vendor's model and each employer's weights are not public** (Oct 14 2026). HiredScore's A threshold is unpublished (Workday, ats-sources.md). So the kit invents no employer weights.
- **Recency:** recent experience carries more weight than older roles (Jan 11 2026). The kit grades a skill seen only in roles that ended 5+ years ago as stale (Jan 11 2026 "recency decay: 5+ years ago score lower"; hashflag's stale grade).
- **Chronology:** systems flag employment gaps, short tenure and career progression for review (Jan 11 2026; Oct 7 2026). The kit flags gaps over 6 months and roles under a year for you to explain; it doesn't score them (thresholds: Jan 11 2026, chat only).

## They read more than the resume

- Rankers and recruiters read LinkedIn and GitHub alongside the resume, and the resume, LinkedIn and GitHub have to tell the same story with matching titles, dates and skills (Oct 7 2026 Block A; Sept 17 2026).
- ATS are no longer only databases with keyword search; they also use AI to screen, and they score with data from GitHub and LinkedIn, such as activity tied to the job posting (Jerome, Nov 8 2026, **chat only**: no vendor document in ats-sources.md says which systems score GitHub activity or how).
- The data contracts: LinkedIn Apply Connect sends a candidate's profile and skills-match data to certified ATS partners; the GitHub REST API serves public profiles and repos to anyone, 60 requests an hour without a token (`references/sources.md`, checked Nov 6 2026).

## Old tricks backfire

White text, font-size-zero keyword blocks, hidden PDF layers, invisible tables, keyword mirroring without substance, title inflation and acronym stacking. Some implementations now flag manipulation, which makes hidden keywords a liability ("Resume tricks for ATS systems", Mar 12 2026; Sept 17 2026).

## Machine first, then the human

Your resume serves two audiences in order: the ATS (keywords, structure, exact matches, format) and then a human (narrative, accomplishments, readability). Satisfy the machine first, then impress the human (Feb 3 2026). Failing the machine is binary; you're out ("AI and taxonomies in specialized recruiting", Jan 2 2026). Jerome's framing in that chat: the ATS layers are deterministic and the human is probabilistic.

## It's regulated

New York City requires employers using automated screening to get a yearly independent bias audit and publish the results (Oct 14 2026; NYC rules in ats-sources.md). It tells you who uses AI screening, not how they score.

## Not used, and why

| Claim | Where it appeared | Why it's out |
|---|---|---|
| "An ATS-optimized resume has 5-10% worse human appeal; a human-optimized one 80-90% worse ATS performance" | Jan 2 2026 chat | No source; the numbers were estimates |
| "Workday heavily weights exact keyword matches in a dedicated Skills section" and "prioritizes exact job title matches" | "Pivoting Hardaway Technologies to civilian job search", Jan 17 2026 | No Workday document says this. Job titles as a criterion is kept, from Greenhouse's docs |
| "Fill out both the Workday profile fields and upload your resume; don't assume one populates the other" | Jan 17 2026 | Chat only; reasonable, but not vendor-documented. Fine as a tip, not as a claim |
| The 7-dimension resume rubric labeled "based on Harvard Business Review research" | Jan 2026 Streamlit scorer | No HBR source existed (Oct 14 2026). Never cite HBR |
| "Applications per hire have tripled since 2021"; "AI mentions up 163%" | Oct 7 and Sept 17 2026 | No source found |
| Skills taxonomies named as Lightcast | Jan 11 and Oct 7 2026 | Not public for civilians (Nov 6 rule). The kit uses O*NET |

## How the kit's resume scorer follows this

| Scorer step | From |
|---|---|
| Parse gate first; a failed gate means no score. A missing email or phone is a fix, not a block | Parsing is the gate (Sept 17); HiredScore gives no grade to unreadable files |
| Score counts the best 10 lane skills, weighted by demand | VWC design judgment: no one resume proves every skill an occupation uses. Configurable (`--need`) |
| Parse-breaker checks: columns, special characters, standard headings, contact info in the top lines, dates | What breaks the parser (Feb 3, Feb 4, Jan 11) |
| Lane skills pulled live from O*NET (plus your saved postings), with BLS outlook beside them | Oct 14 2026: "O*NET posting share and importance values, with BLS outlook reported alongside" |
| Each skill graded proven 1.0, applied 0.7, listed 0.4, stale 0.3, none 0. Proven needs a resume bullet with a number AND the same skill in a pinned repo pushed in the last year or in LinkedIn Experience, Projects or Featured | Evidence over lists (Sept 17); signal strength (Feb 3); recency (Jan 11); rankers read LinkedIn and GitHub alongside the resume (Oct 7, Sept 17); AI screeners score GitHub and LinkedIn activity against the posting (Nov 8 2026, chat only). The one-year window is a VWC design judgment |
| Screen Grade per posting: knockouts, basic and preferred quals one at a time with exact quotes, A to D | HiredScore and Greenhouse docs; Oct 14 2026 scoring mechanism |
| Chronology and manipulation flags, reported, not scored | Jan 11 2026; Mar 12 2026; Sept 17 2026 |
