---
description: "Run the whole scoring chain in one go (resume, LinkedIn, GitHub, portfolio) and show the combined report: the total, the machine read, the human read and the resume gate."
argument-hint: "[work folder, default ~/job-search]"
---

Run `scripts/score_all.py` from this kit against the work folder: $ARGUMENTS (default `~/job-search`). The folder must be outside any git repo (the script refuses otherwise).

1. If the folder has no `score-all.json`, this is a first run: ask for the resume file, the role, and whichever of these they have (LinkedIn PDF or text file, GitHub handle and pinned repos, portfolio URL), then pass them as flags. Otherwise run it with `--dir <folder>` and nothing else.
2. Show what it printed, as printed: the line for each surface, then the total, the machine read, the human read and the resume gate. Don't round, re-add or reword the numbers.
3. Then give the three highest-gain fixes from `plan.md` in the folder.

Live data only. If a surface is named as not scored, say which one and why, and don't fill it in from an older file. If the run stops, show the `REFUSED:` or `STOPPED:` line and what to do about it.
