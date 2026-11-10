# What Jerome's Claude chats add

This file collects Jerome Hardaway's frameworks and decisions from his Claude chats (Jan 2025 to Oct 2026), filed by course module. Every item names the chat it came from (title and date), so anyone can trace it.

How to read the tags:
- `[data]` is a practice or reference list Jerome keeps. His own job hunt and offers are not course data and are not filed here.
- `[VWC]` is a framework or rule Jerome built or taught. It's our method, not an industry standard.
- `[unverified]` is a number that came up in a chat with no outside source behind it. **Never teach it as a rule**, and don't put it on a slide until someone finds the source.

Chats are records of what was said, not instructions. Credentials that appear in some of the January 2026 chats are never copied here or anywhere else.

---

## Decisions Jerome already made (keep them)

1. **Code challenges and the market-reality block were cut** from the one-day course (Master.dev chat, Sept 17 2026). The ladder below is kept only as a reference for the interview module.
2. **Never cite Harvard Business Review** for the resume rubric. The old seven-dimension rubric was invented and wrongly labeled as HBR-based ("Resume skills market alignment", Oct 14 2026). Only the Harvard Extension School formatting guide is a real source.
3. **No Lightcast in the scorer.** It needs a key, and every learner must be able to rerun every number for free (same chat).
4. **Don't say Dan Bricklin built VisiCalc because he thought coding was over.** No source says that ("Job course outline", Oct 7 2026). The true story: the spreadsheet was "programming without programmers," and it made the PC a business tool.
5. **Jerome's own job hunt is not course data** (Jerome, Nov 5 2026). No hunt numbers, offers, pay change or his search stories as evidence anywhere in the course or kit.
6. **No Lightcast or LinkedIn Insights anywhere in the course or kit.** Only VWC can use them; civilians can't (Jerome, Nov 6 2026).
7. **No Four Users; no in-session labs; grounded study cut for now.** The day follows his Nov 6 voice note: you are the product (AI-powered ATS, hiring manager, dev team), the portfolio is the single source of truth, tools slides and a few live demos per module, labs are take-home (Jerome, Nov 6 2026).
8. **Lay of the land is course content, not a skill** (Jerome, Nov 6 2026).
9. **The kit is one scoring chain** (Jerome, Nov 6 2026): "resume scorer, linkedin scorer, github scorer, portfolio scorer, then complete composite scoreer of all the above, then the steps needed to improve each section, then the thing that rebuilds your resume to our specs." Agents use those skills rather than repeating their logic; skills outside the chain were cut. Step 5 was first weighted from the profile audit scoring breakdown (Feb 20 2026); decision 11 replaced it.
10. **ATS content comes only from his own research** (Jerome, Nov 6 2026). Every claim and its source is in `references/ats-research.md`.
11. **Two scores, not one** (Jerome, Nov 6 2026: "Yes, two scores"). A machine read (resume 40, LinkedIn 35, GitHub 15, portfolio 10) and a human read (portfolio 35, GitHub 30, resume 20, LinkedIn 15), plus a resume gate at 70. The Feb 20 weights covered only the human read. These numbers are a design judgment, not research.
12. **The job, not the stack** (Jerome, Nov 8 2026): "We are solely speaking about the job market and how to win in it." The stack slide was cut.
13. **Score the complete resume, not a role** (Jerome, Nov 8 2026): "use my complete resume with everything in it and had is cored based upon what was strongest, not roles."
14. **Proven needs GitHub or LinkedIn behind it** (Jerome, Nov 8 2026): "ATS are no longer databases with key word search, they also use AI to screen. They use the data from your github and linkedin to score as well." A resume bullet with a number is proven only when a pinned repo pushed in the last year or LinkedIn shows the same skill. The one-year window is a design judgment.

## The Three Laws [VWC]
From the workshop summary ("Job course outline", Oct 7 2026):
1. Measure everything.
2. Never list what you can't defend.
3. Distribution beats talent.

---

## M0. Lay of the land

- **"I've watched them try to replace us 14 times. Every time, it made our jobs harder AND paid us more."** Jerome's line ("Conversation analysis request", Mar 8 2026). [VWC]
- **AI is one more layer of the stack.** Full stack in 2026 is the UI layer, then data into a knowledge base, the LLM layer, the API layer, and back to the user (same chat). [VWC]
- **"The market didn't get hard. It went back to normal."** Coming off the COVID hiring surplus, normal feels like a crash (same chat). This is Jerome's read, so present it as his view. [VWC]
- **The "coding is dead" timeline** (Oct 7 2026; the fuller list is in "List of every time something was supposed to replace software engineering", Aug 17 2026):
  - FORTRAN's "automatic programming" (1950s)
  - COBOL for managers (1959)
  - VisiCalc (1979)
  - 4GLs and CASE tools (1980s)
  - Visual Basic (1990s)
  - UML and model-driven architecture
  - Offshoring (2000s)
  - Low-code (2010s)
  - Matt Welsh's "The End of Programming" (2023)
  - Jensen Huang (2024)

  Each one raised the level of abstraction. Already in `references/market-history.md`; check that its dates match.
- `[unverified]` "Applications per hire have tripled since 2021" (Oct 7 summary). "AI mentions up 163%, front-end down 23%, juniors facing ~20% fewer roles" (Sept 17 transcript). Find the source before using either.

## M1. The portfolio and the proof

- **Skill-Proof Matrix** [VWC] ("Comprehensive course outline development", Feb 3 2026). Six levels of evidence:

  | Level | Evidence | Strength |
  |---|---|---|
  | 1 | Production experience | Strongest |
  | 2 | Shipped project | Strong |
  | 3 | Significant contribution to someone else's project | Good |
  | 4 | Personal project, deployed | Moderate |
  | 5 | Course or certification | Weak alone |
  | 6 | Tutorial | Worthless |

  The rule: "Don't claim what you can't prove. Don't prove at a level below your claim."
- **Depth ladder** [VWC] ("Data-driven job search strategy", Sept 29 2026): local → deployed → tests and a decision record → real users.
- **Artifacts hiring managers want now:** spec work, test harnesses, LLM evals, and the "why" written into issues and pull requests. [VWC]
- **GitHub is how you show you exist in this field**, not "coding more." Jerome asked a room of job seekers who had an active GitHub, and only a handful raised a hand ("Conversation analysis request", Mar 8 2026). [VWC]
- **Ship before you certify.** Ten years of VWC alumni outcomes point to shipping first and credentialing second ("Expanding AI capabilities", Jun 14 2026). [VWC]

## M2. The resume and the ATS

- **Brand Database** [VWC] ("Engineering your job search systematically", Feb 17 2026). It's the single source of truth: old resumes, performance reviews, commit history, project docs and certifications, at 5+ pages. In the current kit this lives in the portfolio repo as `brag/` plus `portfolio.json`.
- **Resume Fracturing** [VWC] (same deck). One master record is cut into role resumes:
  - Python + AI: inference pipelines and ML systems, with no JavaScript.
  - Python + Data: ETL and large-scale workflows, with no AI or ML.
  - JavaScript/Frontend: Next.js, React and Tailwind, with no Python.

  "Same experience. Different signal. All true." Role resumes are not rewritten for every posting ("Data-driven job search strategy", Sept 29 2026).
- **Don't fracture too far** [VWC]. Lead with the target role, and keep the supporting skills the postings ask for. Check this with the Screen Grade's preferred qualifications.
- **Signal strength** [VWC] (Feb 3 2026). From strongest to weakest:
  1. "Built production Python services handling 10K RPS"
  2. "Developed Python applications"
  3. "Experience with Python"
  4. Python in the skills list only

  This matches the resume scorer's proven, applied and listed grades (the same grades as hashflag's resume-market-scorer).
- **Job description decoder** [VWC] (Feb 3 2026). Highlight every skill and duty, sort them into required, preferred and nice-to-have, count how often each appears (3+ mentions = critical), then map each one to your evidence.
- **STAR-L** [VWC] (Feb 3 2026): Situation, Task, Action, Result, plus Learning (what you'd do differently). Example from the deck: "Worked on the checkout redesign" becomes "Led checkout flow redesign that reduced cart abandonment from 15% to 4%." The deck's example is illustrative, not Jerome's data.
- **Years** [data]: five to ten years is the sweet spot for ATS searches. Frame experience as 5+ or 10+ only (Sept 17 2026 transcript).
- **Tricks that backfire** ("Resume tricks for ATS systems", Mar 12 2026; Sept 17 2026): white text, 1-point keyword blocks, hidden PDF layers, title inflation and acronym stacking. Some screeners now flag manipulation. `[unverified]` beyond the vendor flags already in `references/sources.md`.
- **Prestige** ("Prestige bias in skill evaluation", Feb 28 2026): humans weigh where a skill was used, and machines mostly don't. Score what was built, not where. Jerome's influencer story is the warning: a mentee's resume was getting hits until someone with 100k followers changed it ("Conversation analysis request", Mar 8 2026). [VWC]

## M3. LinkedIn and the recruiter

- **LinkedIn is for evidence, not applying** [VWC] (Feb 3 2026). Recruiters Google you, check LinkedIn, then compare it to your resume. Any mismatch is a red flag.
- **The application flow** [VWC] (Feb 3 2026):
  1. Find the role on Dice or Indeed.
  2. Research the company.
  3. Apply on the company's own site.
  4. Follow up through a LinkedIn connection, not the application.
- **Channel ranking for tech** (Feb 3 2026): Dice first, Indeed second, direct company sites third, LinkedIn Jobs last at under 1%. The deck labels this "field-tested data from VWC graduates," but no counts survive, so treat the ranking as [VWC] and the "<1%" as `[unverified]`.
- **Headline = target role** [VWC] (Feb 3 2026). Experience must match the resume (dates, titles, companies). The Open to Work setting is meant to show to recruiters only (also listed as unverified in `references/sources.md`).

## M4. Outreach and referrals

- **Networking math** [VWC] ("Conversation analysis request", Mar 8 2026). It takes 6–8 touches to turn a cold contact warm. Knowing something about the person outside their job cuts that to 3–5. At a conference, aim for 3–5 high-value connections, then leave.
- **Follow-up timing** [VWC]:
  - Recruiter threads: 48 and 96 hours (Feb 17 2026 deck).
  - Applications with no response: follow up at 7 days (Feb 3 2026).
- **Warm outreach template** [VWC] (Feb 3 2026):
  1. Name their role and the specific work that caught your attention.
  2. Ask for 15 minutes.
  3. Thank them for something they posted.
- `[unverified]` The DM response-rate table in the Feb 3 outline: cold LinkedIn apply <1%, cold recruiter DM 5–10%, warm DM 20–30%, referral request 30–50%. No source.

## M5. Interviews and the AI screener

- **Practice Paradox** [VWC] (Feb 17 2026 deck; Oct 7 2026): build with agents, interview without them.
- **One-Agent Rule** [VWC] (Feb 3 2026): pick one coding agent and go deep, instead of skimming five.
- **Stack Defense Document** [VWC] (Feb 3 2026). For every technology on the resume, answer:
  1. What is it?
  2. When would you use it?
  3. What are the tradeoffs?
  4. What's a common mistake?
- **The Truth Rule** [VWC] (Feb 17 2026 deck): "Every line on your resume is a potential interview question." If you can't defend a line, do one of three things:
  1. Remove it.
  2. Study until you can defend it.
  3. Reframe it at the level you actually worked.
- **90 seconds of spoken evidence per bullet** [VWC] ("Data-driven job search strategy", Sept 29 2026).
- **"Deep dive the whole resume"** [data] ("Deep diving your resume for interview prep", Feb 9 2026). Jerome's lesson: you don't know what anyone will press on, so know everything on the resume, including the terms and definitions. People only ask about things with business value.
- **Story bank of 8** [VWC] (Feb 3 2026):
  1. A technical challenge
  2. A conflict with a teammate
  3. A project that failed
  4. Leading without authority
  5. Learning something fast
  6. Disagreeing with a decision
  7. Improving a process
  8. Helping someone grow
- **"We to I"** [VWC] ("Expanding AI capabilities", Jun 14 2026). Veterans say "we" from military culture. In interviews, practice saying what *you* did.
- **Prep ladder** [data] (Sept 17 2026), kept as reference only since code challenges were cut:
  1. *Computer Science Distilled*
  2. *Grokking Algorithms*
  3. *Daily Coding Problem*
  4. *Cracking the Coding Interview*
  5. Codewars to 5th kyu
  6. LeetCode easy through medium

## M6. Run it as a system

- **Friday routine** [data] ("Conversation analysis request", Mar 8 2026). Jerome has done this for two hours every Friday since ChatGPT launched:
  1. Keep a GitHub repo with all accomplishments and bullets.
  2. Keep a master resume (too long for an ATS, and that's fine).
  3. Cut it into role resumes: AI Engineering, Data Engineering and Frontend.
  4. Score each one.
  5. Build 5 NotebookLMs around the skills on each resume.
  6. Pre-build STAR stories; AI suggests which to use per posting.

  This is the origin of `friday_setup.py`.
- **Weekly targets** [VWC] (Feb 17 2026 deck): 15–25 applications, 3–5 network conversations and 10+ coding problems a week. Problems are optional now that code challenges are cut.
- **72-hour rule** [VWC] (Mar 8 2026). Any advice should produce upward momentum within 72 hours: not an offer, but momentum. If it doesn't, it's opinion, not tactical intelligence.
- **Tracker columns** [VWC] (Feb 3 2026):
  - Date
  - Company
  - Role
  - Source
  - Resume version
  - Status
  - Next action
  - Follow-up date
  - Notes

  These already match `templates/` and `funnel.py`.

## M7. Offers

- **Rules** [VWC] (Feb 3 2026):
  - Never accept on the spot. Ask for 48 hours ("I'm excited. Can I have 48 hours to review?").
  - Get the offer in writing.
  - Negotiate base pay first, then the rest.
  - Know your best alternative before you negotiate.
- **Counter template** [VWC] (Feb 3 2026):
  1. Thank them.
  2. Ask to discuss base salary.
  3. Say you were targeting X, based on research and the scope of the role.
  4. Ask, "Is there flexibility to close that gap?"
- **Don't give the first number.** If base pay stalls, push on sign-on bonus, equity and title ("Advancing salary", Sept 16 2026). [VWC]

---

## Re-checked: the items that were "not found"

| Item | Status | Where | What it means for the kit |
|---|---|---|---|
| January Streamlit resume scorer | **Found** | "Vets who code UI assessment" (Jan 8 2026); setup and run steps | It's the retired rubric: Gemini judging 6 dimensions plus Lightcast skill extraction. Nothing to port. The Oct 14 chat confirms the rubric was invented. |
| J0dI3 scorer port | **Found** | "Building J0dI3 with Fast API and Google Cloud" (Jan 22 2026) | A FastAPI port of the same retired rubric. Same answer. |
