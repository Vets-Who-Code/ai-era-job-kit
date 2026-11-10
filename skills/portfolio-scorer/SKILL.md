---
name: portfolio-scorer
description: "Step 4 of the scoring chain. Scores a portfolio site: the automated checks a script can verify (title, description, HTTPS, mobile, alt text, contact, artifact pages, live links), then the judgment pass against the Vets Who Code Portfolio Checklist, with a ranked fix list. Use when someone asks to score, review or check their portfolio or personal site, or asks \"is my portfolio ready to share\"."
---

# Portfolio scorer (step 4 of 7)

`$KIT` is two folders up from this skill's base directory. The portfolio is the base of the whole job search and the single source of truth: every resume line, LinkedIn field and GitHub pin points back to it.

## Run it
1. Automated pass (leave `--github` off in the chain; step 3 scores GitHub):
   `python3 $KIT/scripts/portfolio_audit.py --url <site> --portfolio <repo>/portfolio.json --json portfolio-score.json`
   It reads the home page and up to five project pages as raw HTML, checks each deployed artifact in `portfolio.json` is on the site, and loads each live link. If the site is drawn by JavaScript it says so and leaves out the checks it couldn't make; cover those in the judgment pass.
2. Judgment pass: open the Vets Who Code Portfolio Checklist (https://vetswhocode.io/portfolio-checklist) and read each section's items on the page itself, not from memory. "The portfolio is a sales site." "You have 8 seconds."
   Write each item you checked to `checklist.json` as `{"section", "item", "pass": true|false, "quote": "<what you saw on the page>"}`, then rerun the script with `--checklist checklist.json` so the judgment is in the score. Every item needs a quote, pass or miss; the script refuses one without.
3. Signal match: `python3 $KIT/scripts/sync_check.py --portfolio <repo>/portfolio.json --resume <file> --linkedin <file> --github <handle> --md sync.md`. Step 5 reports it beside the score.
4. Report the automated score, each checklist section as passed out of checked (quote what you saw for each miss), and the top five fixes, highest leverage first. Don't call it ready until it clears the checklist's Quality Bar.

## Jerome's playbook
- Grade each claimed skill by its best evidence (Skill-Proof Matrix).
- Ship before you certify.
- Artifacts teams want now: spec work, test harnesses, LLM evals, and the "why" written into issues and pull requests.
- The Brag Database lives in the portfolio (`brag/entries`); Friday Setup feeds it.

## Tone and rules
Lead with what works, then the fixes. Quote what you saw; never guess at pages you couldn't load. For a hiring-manager read that isn't anchored on yours, use the `dev-team-reviewer` agent.
