---
description: "Show where you are in the scoring chain and run the next step."
---

Walk the person through the kit in order. Check which outputs already exist in the current folder and their portfolio repo (portfolio.json, brag/entries, resume-score.json, linkedin-score.json, github-score.json, portfolio-score.json, sync.md, composite.json, plan.md, the rebuilt resume). Report the first missing step in one line and offer to run it:

0. Portfolio repo, the single source of truth: copy `templates/portfolio.json` and `templates/portfolio-repo/gitignore`, then `scripts/friday_setup.py` and the `brag-curator` agent for the Brag Database.
1. `resume-scorer` -> resume-score.json (live O*NET and BLS), plus a Screen Grade per posting
2. `linkedin-scorer` -> linkedin-score.json
3. `github-scorer` -> github-score.json
4. `portfolio-scorer` -> portfolio-score.json and sync.md
5. `composite-scorer` -> composite.json (machine read, human read, resume gate)
6. `improvement-plan` -> plan.md (fix at the source: portfolio first)
7. `resume-rebuilder` -> rebuilt resume, `--check`, defend every line, rescore

The `career-scorecard` agent runs 1 to 7 in one go.

Once the chain is done, run the weekly loop in this order and report which step is next:

1. Friday Setup: `scripts/friday_setup.py`, then `brag-curator` to promote the week's wins.
2. Sync check: `scripts/sync_check.py`. Four sources, one story; fix the portfolio first.
3. Funnel review: `scripts/funnel.py report`. Name the break point and the layer to fix.
4. Postmortem: one per loss, blameless (`funnel.py postmortem`, `templates/postmortem.md`).
5. Reallocate toward the source that converts.

72-hour rule: a fix with no upward movement in 72 hours was opinion, not tactical intelligence. Say so, and pick the next fix.

$ARGUMENTS
