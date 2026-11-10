# How every tool in this kit is built

The bar is the resume-market-scorer in [Vets-Who-Code/hashflag-skills](https://github.com/Vets-Who-Code/hashflag-skills/tree/main/skills/resume-market-scorer): live data pulled by script on every run, a fixed formula written down, every grade backed by a quote, and a measured check that two graders land in the same place. Every skill, agent and script here follows the same six rules. How the ATS works, claim by claim with its source: `references/ats-research.md`.

1. **Live data or stop.** Market numbers (O*NET, BLS, postings, layoffs) are pulled by a script on the run that uses them. If the pull fails, the tool prints `STOPPED:` and gives no number. Nothing is scored from memory.
2. **Every number that backs a "why" names its source**, with one of four tags. Stories and frameworks don't need one: data is for why to do a thing, not for the story.
   - `[vendor]`: documented by the company that runs the screen, or by a law or regulator (Workday HiredScore, Greenhouse, Eightfold, LinkedIn Help, NYC Local Law 144, EEOC).
   - `[HES]`: Harvard Extension School, *Resumes and Cover Letters* (Mignone Center for Career Success, 2024).
   - `[data]`: a dated public dataset (vendor and law sources are in `references/sources.md`). Jerome's own job hunt and offers are not course data and are never used as evidence.
   - `[VWC]`: a Vets Who Code definition. These are our choices, not industry standards, and every report says so.
   - Frameworks and numbers from Jerome's Claude chats are filed in `references/jerome-chat-archive.md`, each citing its chat. Any figure marked `[unverified]` there is never used as a rule until someone finds its source.
3. **Evidence is a quote.** A grade of "met", "proven" or "pass" needs an exact quote from the resume, profile, repo or transcript. No quote means not met. Scripts refuse quotes that aren't in the text.
4. **Rubrics have thresholds, not vibes.** Each rubric says what earns each level and what the pass line is. If a level can't be checked from evidence, it isn't in the rubric.
5. **Grading disagreements get measured.** Where a person or an AI grades (resume skills, interview answers), the tool says how consistency was measured and the target spread. Rules get tightened until graders agree; the rule is never bent for one person.
6. **Not a hiring prediction.** Employers set their own weights and don't publish them. Every score says what it mirrors and that it is not a promise.

## What we don't use, and why

- **The old seven-dimension resume rubric** (Quantification, Action Verbs, Relevance, Clarity, Impact Statements, ATS Optimization, Harvard Formatting). Six of those dimensions were never tied to a published source, and the scores were model opinions with no formula. Only the Harvard formatting rules had a real source, and those live on as `[HES]` checks.
- **Licensed or keyed data sources** that learners can't access on their own. Every learner has to be able to rerun every number for free, so the course and the kit use only public data: O*NET, BLS and public job postings.
- **Grading tone, accent, pauses or facial expressions** in interview practice. AI interview vendors exclude these from scoring, and they are unreliable across speech patterns.

## You are the product

You're not a user of the hiring process. You are the product moving through it, in sequence: an AI-powered ATS, then a hiring manager, then the dev team over multiple rounds of interviews. Each stage reads what the last one passed along. (Jerome's frame, Nov 6 2026.) Your portfolio is the knowledge base everything is built from.

| Stage | What it does | How it scores (source) | Kit tools |
|---|---|---|---|
| 1. AI-powered ATS | Parses your file, runs knockout questions, grades you against the posting | Knockout questions screen first; the parser fills fields; an AI ranker grades the resume against basic and preferred qualifications, A to D (HiredScore) or by match category (Greenhouse) [vendor] | `resume-scorer` (`resume_score.py`, `screen_grade.py`), `ats-screener` |
| 2. Hiring manager | Reads what the ATS passed along and checks you're consistent | Recruiters search LinkedIn Recruiter with filters (skills, job title, location, open to work) [vendor]; they Google you, check LinkedIn and compare it to the resume, and any mismatch is a red flag [VWC]. AI interviewers they configure score a transcript against their rubric [vendor] | `linkedin-scorer`, `sync_check.py`, `recruiter-screen`, `ai-interviewer` |
| 3. Dev team | Multiple rounds of interviews | Probes any line on the resume; reads code, decisions, tests and evals; asks why [VWC] | `github-scorer`, `portfolio-scorer`, `resume-rebuilder` (defend every line), `dev-team-reviewer`, `final-round-panel` |
