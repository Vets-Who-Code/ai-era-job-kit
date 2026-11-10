# Take-home labs

No labs run during the live session. Do these after, in order. You don't need to finish them all in one week: start with module 1 and work down.

| # | Module | Take-home lab | Tools |
|---|---|---|---|
| 1 | Score your skills | Save 10 real postings for your lane into `postings/`, run step 1 of the chain on your resume, and mark each skill "can prove now" or "need proof" from its grade. | `resume-scorer`, `resume_score.py`, `market_snapshot.py`, `/score-resume` |
| 2 | How the ATS parses, and how resumes are read | Run the parse test on your resume (extract the text and check the order), decode one real posting (highlight, sort, count, map), then run a Screen Grade against it and note every qualification marked Not Met. | `resume-scorer`, `screen_grade.py` (`split` counts mentions: 3+ is critical), `ats-screener` |
| 3 | Your resume | Rebuild one lane resume from your portfolio record with the lift list, fill every [ask] and run the spec check. Save the PDF outside any repo. | `resume-rebuilder`, `resume_rebuild.py`, `resume_score.py` |
| 4 | Your portfolio: the single source of truth | Run your first Friday Setup and curate five Brag Database entries. Pin only manicured repos, then run steps 3 and 4: the GitHub score, the portfolio score and the sync check. | `friday_setup.py`, `brag-curator`, `github-scorer`, `github_score.py`, `portfolio-scorer`, `portfolio_audit.py`, `sync_check.py` |
| 5 | LinkedIn | Score LinkedIn against the same target (step 2), fix it to match your portfolio, then run the two scores and the improvement plan (steps 5 and 6). | `linkedin-scorer`, `linkedin_score.py`, `composite-scorer`, `improvement-plan`, `scorecard.py`, `recruiter-screen` |
| 6 | AI interviewers and defending every line | Run one mock AI screen on your rebuilt resume, grade every line Defended, Thin or Cut, rerun your two weakest answers, and build a Stack Defense Doc. | `/mock-screen`, `ai-interviewer`, `resume-rebuilder`, `final-round-panel`, `story-table.md`, `stack-defense.md` |
| 7 | Funnel, postmortems and offers | Start your funnel tracker, write one blameless postmortem, fill the offer matrix for a real or sample offer, and rerun the whole chain to see what moved. | `funnel.py`, `postmortem.md`, `offer-matrix.md`, `career-scorecard`, `/job-hunt` |

Keep resumes and `funnel.csv` outside any git repository.
