# AI-Era Job Kit

**Bottom line:** a free, portfolio-first toolkit for getting a software engineering job in the AI era. Your portfolio is the base; your resume, LinkedIn and GitHub are scored against the market and rebuilt from it. One scoring chain of 7 skills, 7 agents that use those skills, 3 commands and 11 no-dependency Python scripts. All market data is public, keyless and pulled live on every run. Every number behind a "why" names its source: see `METHOD.md`.

**The Three Laws:**
1. Measure everything.
2. Never list what you can't defend.
3. Distribution beats talent.

Built for the *Job Hunting in the AI Era* workshop on Master.dev (formerly Frontend Masters).

## Install (pick one)

1. **As a Claude Code plugin** (once this folder is published to a GitHub repo):
   ```
   /plugin marketplace add <owner>/<repo>
   /plugin install ai-era-job-kit@ai-era-job-kit
   ```
2. **Copy into your user config** so it works in every project:
   ```
   cp -r skills/* ~/.claude/skills/
   cp agents/*.md ~/.claude/agents/
   cp commands/*.md ~/.claude/commands/
   ```
   Keep `scripts/` and `templates/` next to `skills/` (skills look two folders up for them), or set the path when asked.
3. **Other AI tools:** each `skills/*/SKILL.md` is plain Markdown instructions; paste or load it into any assistant that supports skills or custom instructions. The scripts run anywhere Python runs.

Docs: Claude Code skills https://docs.claude.com/en/docs/claude-code/skills · subagents https://docs.claude.com/en/docs/claude-code/sub-agents · plugins https://docs.claude.com/en/docs/claude-code/plugins

## Requirements

- Python 3.10+ (standard library only, nothing to `pip install`)
- GitHub CLI for Friday Setup: https://cli.github.com, then `gh auth login` (the GitHub scorer needs no account or token)
- Optional: `pdftotext` (poppler) to read PDF resumes; otherwise use `.docx` or `.txt`
- Optional: `export JOBDATA_CONTACT=you@example.com` so data providers can reach you if your script misbehaves

## Four sources of truth

Your portfolio holds the master record: `portfolio.json` (profile, experience, artifacts) and the curated Brag Database in `brag/entries/`. GitHub, your resume and LinkedIn are built from it and must agree with it.

1. A win happens. Friday Setup pulls it into `brag/inbox/`; you curate and promote it to `brag/entries/`.
2. If it changes a project or a role, update `portfolio.json`.
3. Rescore and regenerate what it touches with the scoring chain below: the resume (`resume-rebuilder`), LinkedIn (`linkedin-scorer`), GitHub (`github-scorer`).
4. Run `scripts/sync_check.py`. Fix any mismatch at the portfolio first, then regenerate.

See `templates/portfolio-repo/README.md` for the repo layout.

## The scoring chain (the 7 skills)

Each step is a skill with a script behind it. Steps 2 to 4 reuse step 1's `resume-score.json`, so every surface is scored against the same live O*NET target. Every scorer writes the same JSON shape, so step 5 can combine them.

| Step | Skill | Script | What you get |
|---|---|---|---|
| 1 | `resume-scorer` | `resume_score.py`, `screen_grade.py` | Parse gate, lane score 0 to 100 from live O*NET and BLS, lift per skill; A to D Screen Grade per posting |
| 2 | `linkedin-scorer` | `linkedin_score.py` | LinkedIn score: headline, location, skills, Featured, About, Experience, resume match |
| 3 | `github-scorer` | `github_score.py` | GitHub score from the keyless REST API: profile, pinned repos, lane skills |
| 4 | `portfolio-scorer` | `portfolio_audit.py`, `sync_check.py` | Portfolio score, the checklist pass, and the sync check |
| 5 | `composite-scorer` | `scorecard.py composite` | Two scores: a machine read (resume 40, LinkedIn 35, GitHub 15, portfolio 10) and a human read (portfolio 35, GitHub 30, resume 20, LinkedIn 15), plus a resume gate at 70 |
| 6 | `improvement-plan` | `scorecard.py plan` | The steps to improve each section, biggest gain first |
| 7 | `resume-rebuilder` | `resume_rebuild.py` | Your resume rebuilt to spec from the portfolio, linted, defended, rescored |

The `career-scorecard` agent runs all seven in order. Step 5 gives two scores because two kinds of reader see you in order: machines first, then people. A resume under 70 is flagged whatever the totals say, since a weak resume means no human sees the rest. The weights and the gate are a VWC design judgment, not research and not any employer's; `--machine-weights`, `--human-weights` and `--gate` change them.

## The course, module by module

| # | Course module | Skill | Agent | Script |
|---|---|---|---|---|
| 0 | Intro, history and the lay of the land | | | |
| 1 | Score your skills | `resume-scorer` (the chain, step 1) | `career-scorecard` | `resume_score.py`, `market_snapshot.py` |
| 2 | How the ATS parses, and how resumes are read | `resume-scorer` (Screen Grade) | `ats-screener` | `screen_grade.py` |
| 3 | Your resume | `resume-rebuilder` | `ats-screener` | `resume_rebuild.py` |
| 4 | Your portfolio: the single source of truth (Brag Database, Friday Setup, GitHub, web app) | `portfolio-scorer`, `github-scorer` | `brag-curator`, `dev-team-reviewer` | `friday_setup.py`, `portfolio_audit.py`, `github_score.py`, `sync_check.py` |
| 5 | LinkedIn | `linkedin-scorer`, `composite-scorer`, `improvement-plan` | `recruiter-screen`, `career-scorecard` | `linkedin_score.py`, `scorecard.py` |
| 6 | AI interviewers and defending every line | `resume-rebuilder` (defend every line) | `ai-interviewer`, `final-round-panel` | `story-table.md`, `stack-defense.md` |
| 7 | Funnel, postmortems and offers | `composite-scorer` (rescore) | `career-scorecard` | `funnel.py`, `postmortem.md`, `offer-matrix.md` |

No labs run during the session. Each module's take-home lab is in `TAKE-HOME.md`.

Run `/job-hunt` to see your next step. Shortcuts: `/score-resume`, `/mock-screen`.

## Quick start (in order)

1. Set up your portfolio repo as the source of truth: copy `templates/portfolio.json` and `templates/portfolio-repo/gitignore` (as `.gitignore`) into it, then start the Brag Database: `python3 scripts/friday_setup.py --portfolio ~/code/portfolio --since 2026-01-01`
2. Save 10+ real postings for the roles you want into a `postings/` folder (optional; O*NET alone works).
3. Step 1, resume: `python3 scripts/resume_score.py --resume ~/resumes/me.pdf --onet 15-1252.00 --postings postings --json resume-score.json`
   Per posting: `python3 scripts/screen_grade.py split --greenhouse <board> --job <id> --out quals.json`, grade each qualification with `resume-scorer`, then `python3 scripts/screen_grade.py grade --resume ~/resumes/me.pdf --quals quals.json --grades grades.json --portfolio portfolio.json --md screen.md`
4. Step 2, LinkedIn: `python3 scripts/linkedin_score.py --profile linkedin.txt --market resume-score.json --portfolio portfolio.json --resume ~/resumes/me.pdf --json linkedin-score.json`
5. Step 3, GitHub: `python3 scripts/github_score.py --user yourhandle --repos repo-a,repo-b --market resume-score.json --portfolio portfolio.json --json github-score.json`
6. Step 4, portfolio: `python3 scripts/portfolio_audit.py --url https://yourname.dev --json portfolio-score.json`, then `python3 scripts/sync_check.py --portfolio portfolio.json --resume ~/resumes/me.pdf --linkedin linkedin.txt --github yourhandle --md sync.md`
7. Step 5, two scores and the resume gate: `python3 scripts/scorecard.py composite --resume resume-score.json --linkedin linkedin-score.json --github github-score.json --portfolio portfolio-score.json --sync sync.md --json composite.json`
8. Step 6, plan: `python3 scripts/scorecard.py plan --composite composite.json --md plan.md`
9. Step 7, rebuild: `python3 scripts/resume_rebuild.py --portfolio portfolio.json --brag ~/code/portfolio/brag/entries --market resume-score.json --out ~/resumes/me-backend-resume.txt`, then `--check` the finished PDF.
10. Track every application: `python3 scripts/funnel.py init --file ~/job-search/funnel.csv`

## Data sources (all public, no API key)

| Source | What it gives | Link |
|---|---|---|
| O*NET database (text release) | Occupations, Technology Skills with Hot Technology and In Demand flags, Skills importance | https://www.onetcenter.org/database.html |
| O*NET OnLine | Look up occupation codes | https://www.onetonline.org/find/ |
| BLS Employment Projections | 10-year growth, annual openings, median wage | https://www.bls.gov/emp/tables/occupational-projections-and-characteristics.htm |
| BLS Public Data API v1 | OEWS wages, no registration (small daily quota) | https://www.bls.gov/developers/ |
| Your saved postings, or public Greenhouse, Lever and Ashby boards | What employers ask for right now, including tools O*NET hasn't added | |

**Live-data rule:** the scorers and market tools stop with `STOPPED:` if O*NET or BLS can't be reached. They never fall back to remembered or cached numbers.

## You are the product

You move through an AI-powered ATS, then a hiring manager, then the dev team over multiple rounds of interviews. `METHOD.md` lists what each stage does, how it scores (with sources) and which tool here rehearses it.

## How the resume is scored (two scores)

1. **Lane score, 0 to 100** (`resume-scorer` + `resume_score.py`). Parse gate first: a file the screener can't read gets no score. Then each in-demand skill for the lane, from live O*NET Technology Skills plus your saved postings, is graded on its evidence across the resume, GitHub and LinkedIn: proven 1.0 (named in an Experience or Projects bullet with a number, and shown in a pinned repo pushed in the last year or in LinkedIn Experience, Projects or Featured), applied 0.7 (in a bullet, but missing the number or the outside proof), listed 0.4, stale 0.3, none 0. Steps 2 and 3 write that evidence; the composite applies it, or pass `--github` and `--linkedin` to step 1. BLS outlook is reported beside it. Run it on your complete resume, with everything in it, not a role cut.
2. **Screen Grade, A to D** (`resume-scorer` + `screen_grade.py`). Mirrors Workday HiredScore: parse gate, knockout questions, then each basic and preferred qualification of one posting marked Met or Not Met with an exact quote. A = all basic + more than half of preferred (read it as "A or B"), B = all basic, C = most basic, D = half or fewer. Run it for every application.

How the ATS works, claim by claim with sources: `references/ats-research.md`. Neither score is a hiring prediction. Employers set their own weights and don't publish them.

## Privacy

- Keep resumes and `funnel.csv` outside any git repository. The Brag Database lives in your portfolio repo: raw pulls stay in the git-ignored `brag/inbox/`, and only entries you curate and promote reach `brag/entries/`.
- Nothing in this kit sends, posts or applies for you. Every message is a draft you send yourself.
- `friday_setup.py` redacts tokens, keys, emails, IPs and internal hostnames, and hides private repo names unless you pass `--show-private`.

## Tests

```
python3 -m unittest discover -s tests -v
```
Offline tests with synthetic fixtures cover parsing, demand ranking, every step of the scoring chain (GitHub is stubbed), the screen grade (quote check, letters, parse gate, git refusal), the live-data stop, the funnel tracker and Friday Setup redaction.

## Edit the skill vocabulary

`scripts/jobdata/lexicon.py` holds the curated list of current tools and aliases. Add what your postings mention; posting frequency, not the list, decides weight.
