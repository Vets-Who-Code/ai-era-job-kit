---
name: github-scorer
description: "Step 3 of the scoring chain. Scores a public GitHub profile with the keyless GitHub REST API: bio, website, profile README, recent activity, and each pinned repo's README, decisions, live demo, tests, CI, license and topics, plus whether the pins prove the lane's top skills and match the portfolio. Use when someone asks to score or improve their GitHub, pick pins, write a profile or repo README, or make GitHub recruiter ready."
---

# GitHub scorer (step 3 of 7)

`$KIT` is two folders up from this skill's base directory. GitHub is how you show you exist: it should say what the portfolio says, in code. Rankers read it alongside the resume (`$KIT/references/ats-research.md`).

## Run it
`python3 $KIT/scripts/github_score.py --user <handle> --repos <pinned,repos> --market resume-score.json --portfolio <repo>/portfolio.json --json github-score.json --md github-score.md`
- Pass the pinned repos: the REST API doesn't list pins, so without `--repos` it reads the six most recently pushed and says so.
- No token, no account: 60 requests an hour, about 20 a run. If GitHub can't be reached it stops (exit 3); say so.
- Report the score and the top six fixes. The weights are a VWC rubric; GitHub publishes no hiring score.
- The JSON also carries `skill_evidence`: each lane skill a pinned repo pushed in the last year shows. AI screeners score activity against the posting (Jerome, Nov 8 2026), so step 1 and the composite use it: a resume skill is proven only when GitHub or LinkedIn backs it.

## What good looks like (the fixes point here)
- **Pins:** only manicured repos, fully built and working, each with a live demo (or a video demo when cost or security rules one out). Unpin tutorials, unfinished work and unchanged forks. There's no fixed number.
- **Profile README** (`<handle>/<handle>`), from `$KIT/templates/github-profile-readme.md`: one line on what they build, three artifacts with outcomes and live links, links to portfolio and LinkedIn. Skip vanity stat cards.
- **Repo READMEs**, in order: the problem, why it matters, how it works (diagram, key decisions, tests, CI, evals), live link, how to run it, what's next. Every claim links to the code that implements it.
- **Hygiene:** description, website, topics, license, CI workflow. If a secret was ever committed, rotate it first.

## Jerome's playbook
Skill-Proof Matrix: production > shipped project > significant contribution > deployed personal project > course or cert (weak alone) > tutorial. "Don't claim what you can't prove."

## Never
Never fabricate contributions or activity. Give them the files and the fix list; they commit and push.
