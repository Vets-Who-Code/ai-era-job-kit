# Portfolio repo layout (the source of truth)

```
your-portfolio/                 the repo behind your site
  portfolio.json                master record: profile, links, experience, artifacts, brag paths
  brag/
    entries/YYYY-MM-DD.md       curated, public-safe wins (committed; publish as a "Shipped" log)
    inbox/                      raw Friday Setup pulls (git-ignored, never committed)
  case-studies/<artifact>.md    story + evidence per artifact
  .gitignore                    copy from templates/portfolio-repo/gitignore
```

How the four sources of truth stay in sync:

1. **Portfolio** holds the record. Every win lands in `brag/entries/`, every project in `portfolio.json`.
2. **GitHub** proves it: pinned repos match `artifacts[].repo`; profile bio matches `profile.headline`.
3. **Resume** is generated from it for each kind of role, and saved outside this repo.
4. **LinkedIn** mirrors it: headline, About, Featured and Experience come from the same record.

Run `python3 <kit>/scripts/sync_check.py --portfolio portfolio.json --resume ~/resumes/me.pdf --linkedin linkedin.txt --github you` after any change. Fix mismatches at the source (the portfolio) first, then regenerate the rest.
