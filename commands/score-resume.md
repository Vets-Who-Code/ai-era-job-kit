---
description: "Score a resume with the resume-scorer skill: the lane score from live O*NET and BLS data, plus a Screen Grade for one posting. No editing."
argument-hint: "<resume-file> [O*NET code or job title] [posting URL or file] [portfolio.json]"
---

Use the `resume-scorer` skill with: $ARGUMENTS

If no resume file is given, ask for its path. If no O*NET code or job title is given, ask what role they're applying for. Write `resume-score.json` and `resume-score.md` next to the resume, never inside a git repo (the script refuses).

1. Run the lane score (`scripts/resume_score.py`) for the O*NET code (`--onet`) or job title (`--role`).
2. If a posting is given, run the Screen Grade for it (`scripts/screen_grade.py`).
3. Report the score, the grade and counts, and the five highest-lift fixes, portfolio-proven gaps first.

Live data only; if a pull fails, stop and say so.
