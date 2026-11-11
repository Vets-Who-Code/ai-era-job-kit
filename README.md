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
   cp -r scripts templates references ~/.claude/
   ```
   The last line matters: each skill looks two folders up from itself for `scripts/`, `templates/` and `references/`, so they have to sit next to `skills/`.
3. **Other AI tools:** each `skills/*/SKILL.md` is plain Markdown instructions; paste or load it into any assistant that supports skills or custom instructions. The scripts run anywhere Python runs.

Docs: Claude Code skills https://docs.claude.com/en/docs/claude-code/skills · subagents https://docs.claude.com/en/docs/claude-code/sub-agents · plugins https://docs.claude.com/en/docs/claude-code/plugins

## Requirements

- Python 3.10+ (standard library only, nothing to `pip install`)
- GitHub CLI for Friday Setup: https://cli.github.com, then `gh auth login` (the GitHub scorer needs no account or token)
- Optional: `pdftotext` (poppler) to read PDF resumes and LinkedIn's PDF; otherwise use `.docx` or `.txt`
- Optional: `export GITHUB_TOKEN=$(gh auth token)` if the GitHub scorer hits the keyless limit (60 requests an hour per IP address, shared across a network; a run uses about 20)
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
| 4 | `portfolio-scorer` | `portfolio_audit.py`, `sync_check.py` | Portfolio score (automated checks plus the checklist pass, and the site checked against `portfolio.json`), and the sync check |
| 5 | `composite-scorer` | `scorecard.py composite` | The total (the four scores added together, out of 400), then two scores: a machine read (resume 40, LinkedIn 35, GitHub 15, portfolio 10) and a human read (portfolio 35, GitHub 30, resume 20, LinkedIn 15), plus a resume gate at 70 and each posting's Screen Grade beside them |
| 6 | `improvement-plan` | `scorecard.py plan` | The steps to improve each section, biggest gain first |
| 7 | `resume-rebuilder` | `resume_rebuild.py` | Your resume rebuilt to spec from the portfolio, linted, defended, rescored |

Every surface score (resume, LinkedIn, GitHub, portfolio) includes a 10-point calibration, capped at 100. It stands in for reference material the public kit can't share, and each report says so. It is a VWC design judgment, set in `scripts/jobdata/calibration.py`.

The `career-scorecard` agent runs all seven in order. Step 5 gives two scores because two kinds of reader see you in order: machines first, then people. A resume that scores under 70 on its own text is flagged whatever the totals say, since a weak resume means no human sees the rest. The weights and the gate are a VWC design judgment, not research and not any employer's; `--machine-weights`, `--human-weights` and `--gate` change them. The LinkedIn and GitHub share of the machine read rests on a chat-only claim (`references/ats-research.md`), and the report says so. The Screen Grade is the one score modeled on vendor documents; it is per posting, so the composite reports it beside the two reads without a weight.

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

## Start here: score your resume in 5 minutes

You need Python 3.10+ and your resume as `.pdf`, `.docx` or `.txt`. Nothing to install (PDFs need `pdftotext`: `brew install poppler` on a Mac, `apt install poppler-utils` on Linux).

1. **Make a work folder outside any git repo** and put your resume in it. The scripts refuse to read or write a resume inside a repo, so it can never be committed by accident.
   ```
   mkdir -p ~/job-search && cd ~/job-search
   cp ~/Downloads/my-resume.pdf .
   KIT=~/code/ai-era-job-kit        # wherever this folder lives
   ```
2. **Score it** against the job you want. Name the role in plain words:
   ```
   python3 $KIT/scripts/resume_score.py --resume my-resume.pdf --role "software developer" \
       --json resume-score.json --md resume-score.md
   ```
   Prefer an exact lane? Look up the code at https://www.onetonline.org/find/ and pass `--onet 15-1252.00` instead of `--role`. Have saved job postings? Put them in a folder as `.txt` files and add `--postings postings`.
3. **Read the report** (printed, and saved as `resume-score.md`):
   - The score out of 100, and the title of the lane it matched. Check the title is the job you meant.
   - The skill table. **Grade** is where each skill stands (proven, applied, listed, stale, none). **Lift** is the points you gain by proving it. Work from the top.
   - "Format and parse fixes": do these first. They're quick, and a file the screener can't read gets no score at all.
4. **Fix and rerun** the same command. To move a skill up, name it in an Experience or Projects bullet with a number ("cut the compute bill 35%"). Only add what you can defend.
5. **Lint the file you'll send:** `python3 $KIT/scripts/resume_rebuild.py --check my-resume.pdf`. "Passes the spec." means it's ready.

In Claude Code the same thing is one line: `/score-resume ~/job-search/my-resume.pdf "software developer"`.

No skill reaches **proven** until GitHub or LinkedIn backs it, so a first score in the 60s or 70s is normal. The full chain below adds that proof.

| If you see | It means | Do this |
|---|---|---|
| `REFUSED: keep resumes and their scores outside any git repository.` | The resume, `--json` or `--md` path is inside a repo | Run from `~/job-search` as in step 1 |
| `REFUSED: pdftotext not found` | PDFs need poppler | Install it, or save the resume as `.docx` or `.txt` |
| `No score: fix the format first` | The parse gate failed | Fix each row marked "no" in the table, then rerun |
| `STOPPED: ...` | O*NET or BLS couldn't be reached | Check your connection and rerun; the kit never guesses numbers |
| The lane title is wrong | `--role` matched a different occupation | Pass the exact code with `--onet` |

## Quick start: the full chain (in order)

Run these from your work folder (`~/job-search` above), with `scripts/` standing for `$KIT/scripts/`. The score files quote your resume, so they stay outside git too.

1. Set up your portfolio repo as the source of truth: copy `templates/portfolio.json` and `templates/portfolio-repo/gitignore` (as `.gitignore`) into it, then start the Brag Database: `python3 scripts/friday_setup.py --portfolio ~/code/portfolio --since 2026-01-01`
2. Save 10+ real postings for the roles you want into a `postings/` folder (optional; O*NET alone works).
3. Step 1, resume: `python3 scripts/resume_score.py --resume ~/resumes/me.pdf --onet 15-1252.00 --postings postings --json resume-score.json`
   Per posting: `python3 scripts/screen_grade.py split --greenhouse <board> --job <id> --out quals.json`, grade each qualification with `resume-scorer`, then `python3 scripts/screen_grade.py grade --resume ~/resumes/me.pdf --quals quals.json --grades grades.json --portfolio portfolio.json --md screen.md`
4. Step 2, LinkedIn: `python3 scripts/linkedin_score.py --profile linkedin.txt --market resume-score.json --portfolio portfolio.json --resume ~/resumes/me.pdf --json linkedin-score.json`
5. Step 3, GitHub: `python3 scripts/github_score.py --user yourhandle --repos repo-a,repo-b --market resume-score.json --portfolio portfolio.json --json github-score.json`
6. Step 4, portfolio: `python3 scripts/portfolio_audit.py --url https://yourname.dev --portfolio portfolio.json --checklist checklist.json --json portfolio-score.json` (the `portfolio-scorer` skill writes `checklist.json`), then `python3 scripts/sync_check.py --portfolio portfolio.json --resume ~/resumes/me.pdf --linkedin linkedin.txt --github yourhandle --md sync.md`
7. Step 5, two scores and the resume gate: `python3 scripts/scorecard.py composite --resume resume-score.json --linkedin linkedin-score.json --github github-score.json --portfolio portfolio-score.json --sync sync.md --screen screen.json --json composite.json` (write `screen.json` with `screen_grade.py grade --out`)
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

**Live-data rule:** the scorers and market tools stop with `STOPPED:` if O*NET or BLS can't be reached. They never fall back to remembered numbers. Steps 2 to 4 reuse the skill list step 1 saved in `resume-score.json`, so every surface is scored against one target; rerun step 1 to refresh it.

## You are the product

You move through an AI-powered ATS, then a hiring manager, then the dev team over multiple rounds of interviews. `METHOD.md` lists what each stage does, how it scores (with sources) and which tool here rehearses it.

## How the resume is scored (two scores)

1. **Lane score, 0 to 100** (`resume-scorer` + `resume_score.py`). Parse gate first: a file the screener can't read gets no score (a missing email or phone is a fix, not a block). Then each in-demand skill for the lane, from live O*NET Technology Skills plus your saved postings, is graded on its evidence across the resume, GitHub and LinkedIn: proven 1.0 (named in an Experience or Projects bullet with a number, and shown in a pinned repo pushed in the last year or in LinkedIn Experience, Projects or Featured), applied 0.7 (in a bullet, but missing the number or the outside proof), listed 0.4, stale 0.3, none 0. A number is a quantity (40%, 10,000, $2M), not a digit inside a name (S3, EC2). The score counts your best 10 skills, weighted by demand (`--need`): no one resume proves every skill an occupation uses, so 100 means the lane's ten most-wanted skills are all proven. That is a VWC design judgment. The outside proof is corroboration you supply, not verification. Steps 2 and 3 write that evidence; the composite applies it, or pass `--github` and `--linkedin` to step 1. BLS outlook is reported beside it. Run it on the resume you send for the lane.
2. **Screen Grade, A to D** (`resume-scorer` + `screen_grade.py`). Mirrors Workday HiredScore: parse gate, knockout questions, then each basic and preferred qualification of one posting marked Met or Not Met with an exact quote. A = all basic + more than half of preferred (read it as "A or B"), B = all basic, C = most basic, D = half or fewer. The script refuses a quote that isn't on the resume or that names none of the skills the qualification asks for. `screen_grade.py agree` measures how far two graders agree (target: same letter, 90% of qualifications). Run it for every application.

How the ATS works, claim by claim with sources: `references/ats-research.md`. Neither score is a hiring prediction. Employers set their own weights and don't publish them.

## Privacy

- Keep resumes and `funnel.csv` outside any git repository. The Brag Database lives in your portfolio repo: raw pulls stay in the git-ignored `brag/inbox/`, and only entries you curate and promote reach `brag/entries/`.
- Nothing in this kit sends, posts or applies for you. Every message is a draft you send yourself.
- `friday_setup.py` redacts tokens, keys, emails, IPs and internal hostnames, and hides private repo names unless you pass `--show-private`.

## Tests

```
python3 -m unittest discover -s tests -v
```
Offline tests with synthetic fixtures cover parsing, demand ranking, every step of the scoring chain (GitHub is stubbed), both O*NET layouts, the skill matcher's false positives, the screen grade (quote check, letters, parse gate, grader agreement, git refusal), the live-data stop, the funnel tracker and Friday Setup redaction.

## Edit the skill vocabulary

`scripts/jobdata/lexicon.py` holds the curated list of current tools and aliases. Add what your postings mention; posting frequency, not the list, decides weight.
