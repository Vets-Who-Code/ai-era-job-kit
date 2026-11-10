#!/usr/bin/env python3
"""Friday Setup: pull everything you shipped since last time into your Brag Database.

Part of the AI-Era Job Kit. You run it; you don't have to build it.

What it pulls
  - Merged pull requests you authored (GitHub CLI), public and private.
  - Optional: pull requests you reviewed (--include-reviews) and issues you
    closed (--include-issues).
  - Or plain `git log` from local repos (--git-repos) for work not on GitHub.

Where it writes
  - --portfolio <repo>: into your portfolio repo, the source of truth. Raw
    pulls land in brag/inbox/ (the script git-ignores it for you). After you
    curate a file with the brag-curator agent, --promote moves it to
    brag/entries/, where it is committed and can be published.
  - --out <folder>: any folder outside a git repo (Drive, Obsidian) instead.

What it does with them
  - Redacts secrets and private details (tokens, keys, emails, IPs, internal
    hosts, password=...). Private repo names and links are hidden unless you
    pass --show-private.
  - Skips anything already logged in an earlier run (remembers what it saw).
  - Writes one Markdown file per run with prompts for Impact, Skills and
    Artifact under each item. Markdown works for Google Drive, Obsidian and
    Notion (import).
  - With --out, refuses to write inside a git repository, so raw notes never
    end up on GitHub (override with --allow-repo if you really mean it).
  - --promote only accepts files marked `status: curated` with no open
    placeholders and nothing the redaction rules would still catch.

Examples
  python3 friday_setup.py --portfolio ~/code/portfolio          # since last run (or 7 days)
  python3 friday_setup.py --portfolio ~/code/portfolio --include-reviews --include-issues
  python3 friday_setup.py --portfolio ~/code/portfolio --since 2026-10-01 --org my-org
  python3 friday_setup.py --portfolio ~/code/portfolio --git-repos ~/work/api ~/work/web
  python3 friday_setup.py --portfolio ~/code/portfolio --dry-run   # print, write nothing
  python3 friday_setup.py --portfolio ~/code/portfolio --promote brag/inbox/2026-10-31.md
  python3 friday_setup.py --out ~/BragDatabase                  # a plain folder instead

Then open the new file with the `brag-curator` agent to turn raw items into
accomplishment entries (impact, scope, skills, proof link).

Needs: Python 3.10+, GitHub CLI logged in (https://cli.github.com, then
`gh auth login`) unless you use --git-repos. Nothing is sent anywhere; the
only network calls are the GitHub CLI's own reads.

Exit codes: 0 ok, 1 a source failed, 2 setup problem or a file not ready to promote.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

__version__ = "1.1.0"

STATE = ".friday-setup-state.json"
SEEN_CAP = 5000
GH_TIMEOUT = 90

REDACTIONS = [
    (re.compile(r"\b(ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}\b"), "[REDACTED-TOKEN]"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "[REDACTED-KEY]"),
    (re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), "[REDACTED-AWS-KEY]"),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"), "[REDACTED-KEY]"),
    (re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"), "[REDACTED-SLACK-TOKEN]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"), "[REDACTED-JWT]"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S), "[REDACTED-PRIVATE-KEY]"),
    (re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^\s:/@]+:[^\s@/]+@"), r"\1[REDACTED-CREDENTIALS]@"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[email]"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[ip]"),
    (re.compile(r"\b[\w-]+(?:\.[\w-]+)*\.(?:internal|corp|local|lan|intranet)(?:\.[\w-]+)*\b", re.I), "[internal-host]"),
    (re.compile(r"(?i)\b(password|passwd|pwd|secret|client[_-]?secret|api[_-]?key|access[_-]?key|token)\s*[:=]\s*\S+"),
     r"\1=[REDACTED]"),
]

KIND_LABEL = {"pr": "Merged PR", "review": "Reviewed PR", "issue": "Closed issue", "commit": "Commit"}


class SourceError(RuntimeError):
    pass


# ---------------------------------------------------------------- text helpers

def redact(text: str) -> str:
    for pat, rep in REDACTIONS:
        text = pat.sub(rep, text)
    return text


def clean_body(body: str, limit: int = 700) -> str:
    body = re.sub(r"<!--.*?-->", "", body or "", flags=re.S)
    body = re.sub(r"^\s*- \[[ xX]\].*$", "", body, flags=re.M)  # PR template checkboxes
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    body = redact(body)
    return body[:limit] + ("…" if len(body) > limit else "")


def item_key(it: dict) -> str:
    return it.get("url") or f"{(it.get('repository') or {}).get('nameWithOwner', '')}#{it.get('number', '')}"


# ---------------------------------------------------------------- state and files

def load_state(out: pathlib.Path) -> dict:
    f = out / STATE
    if not f.exists():
        return {}
    try:
        data = json.loads(f.read_text())
    except (OSError, json.JSONDecodeError):
        print(f"warning: {f} is unreadable; starting fresh (duplicates are possible this run).", file=sys.stderr)
        return {}
    return data if isinstance(data, dict) else {}


def last_run(out: pathlib.Path) -> str | None:
    return load_state(out).get("last_run")


def atomic_write(path: pathlib.Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=path.suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        pathlib.Path(tmp).unlink(missing_ok=True)
        raise


def inside_git_repo(path: pathlib.Path) -> bool:
    return any((p / ".git").exists() for p in [path, *path.parents])


PORTFOLIO_IGNORES = ["brag/inbox/", STATE]
PLACEHOLDERS = ("[ask:", "_(what changed", "_(tools and practices", "_(which artifact")


def ensure_portfolio_ignores(repo: pathlib.Path) -> list[str]:
    """Make sure raw pulls and state can never be committed from the portfolio repo."""
    gi = repo / ".gitignore"
    have = gi.read_text().splitlines() if gi.exists() else []
    missing = [x for x in PORTFOLIO_IGNORES if x not in have]
    if missing:
        text = gi.read_text() if gi.exists() else ""
        if text and not text.endswith("\n"):
            text += "\n"
        text += "# Friday Setup: raw, uncurated pulls stay local\n" + "\n".join(missing) + "\n"
        atomic_write(gi, text)
    return missing


def frontmatter_status(text: str) -> str | None:
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    if not m:
        return None
    st = re.search(r"^status:\s*(\w+)", m.group(1), re.M)
    return st.group(1) if st else None


def promote(repo: pathlib.Path, src: pathlib.Path) -> int:
    """Move a curated inbox file into brag/entries after safety checks."""
    src = src if src.is_absolute() else (repo / src)
    if not src.exists():
        print(f"{src} not found.", file=sys.stderr)
        return 2
    text = src.read_text(encoding="utf-8")
    problems = []
    if frontmatter_status(text) != "curated":
        problems.append("frontmatter still says status: raw (curate it with the brag-curator agent first)")
    open_marks = sorted({p for p in PLACEHOLDERS if p in text})
    if open_marks:
        problems.append("open placeholders remain: " + ", ".join(open_marks))
    if redact(text) != text:
        problems.append("something the redaction rules catch is still in the file (a token, email, IP, "
                        "internal host or credential)")
    if problems:
        print(f"Not promoted: {src.name}", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 2
    dest_dir = repo / "brag" / "entries"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if dest.exists():
        print(f"{dest} already exists; rename the inbox file first.", file=sys.stderr)
        return 2
    atomic_write(dest, text)
    src.unlink()
    print(f"Promoted to {dest.relative_to(repo)}. Review it, then commit it with your portfolio.")
    return 0


# ---------------------------------------------------------------- sources

def _run(cmd: list[str], timeout: int = GH_TIMEOUT) -> str:
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise SourceError(f"{' '.join(cmd[:3])} timed out after {timeout}s") from e
    except FileNotFoundError as e:
        raise SourceError(f"{cmd[0]} not found") from e
    if res.returncode != 0:
        raise SourceError(res.stderr.strip() or f"{cmd[0]} exited {res.returncode}")
    return res.stdout


def require_gh() -> None:
    if not shutil.which("gh"):
        raise SystemExit("GitHub CLI not found. Install from https://cli.github.com and run `gh auth login`, "
                         "or use --git-repos for local history.")
    try:
        _run(["gh", "auth", "status"], timeout=30)
    except SourceError as e:
        raise SystemExit(f"GitHub CLI isn't logged in ({e}). Run `gh auth login`.")


def _gh_search(kind: str, extra: list[str], fields: str, org: str | None, limit: int) -> list[dict]:
    """One gh search per visibility, so private items are known to be private."""
    items: list[dict] = []
    for vis in ("public", "private", "internal"):
        cmd = ["gh", "search", kind, *extra, "--visibility", vis, "--json", fields, "--limit", str(limit)]
        if org:
            cmd += ["--owner", org]
        for it in json.loads(_run(cmd) or "[]"):
            repo = dict(it.get("repository") or {})
            repo["isPrivate"] = vis != "public"
            it["repository"] = repo
            items.append(it)
    return items


def gh_prs(since: str, org: str | None, limit: int) -> list[dict]:
    items = _gh_search("prs", ["--author", "@me", "--merged", "--merged-at", f">={since}"],
                       "title,url,body,repository,closedAt,number", org, limit)
    for it in items:
        it["kind"] = "pr"
    return items


def gh_reviews(since: str, org: str | None, limit: int) -> list[dict]:
    me = _run(["gh", "api", "user", "--jq", ".login"], timeout=30).strip()
    items = _gh_search("prs", ["--reviewed-by", "@me", "--merged", "--merged-at", f">={since}"],
                       "title,url,repository,closedAt,number,author", org, limit)
    out = []
    for it in items:
        author = (it.get("author") or {}).get("login")
        if author == me:
            continue  # your own PRs are already counted
        it["kind"] = "review"
        it["body"] = "Reviewed a teammate's pull request."
        out.append(it)
    return out


def gh_issues(since: str, org: str | None, limit: int) -> list[dict]:
    items = _gh_search("issues", ["--author", "@me", "--state", "closed", "--closed", f">={since}"],
                       "title,url,body,repository,closedAt,number", org, limit)
    for it in items:
        it["kind"] = "issue"
    return items


def git_email(repo: pathlib.Path) -> str | None:
    try:
        return _run(["git", "-C", str(repo), "config", "user.email"], timeout=15).strip() or None
    except SourceError:
        return None


def git_commits(repos: list[str], since: str, author: str | None) -> list[dict]:
    out = []
    for r in repos:
        p = pathlib.Path(r).expanduser()
        who = author or git_email(p)
        cmd = ["git", "-C", str(p), "log", f"--since={since}", "--no-merges",
               "--pretty=format:%H%x1f%s%x1f%b%x1f%cI%x1e"]
        if who:
            cmd.insert(4, f"--author={who}")
        try:
            stdout = _run(cmd, timeout=60)
        except SourceError as e:
            print(f"warning: skipped {p}: {e}", file=sys.stderr)
            continue
        for rec in stdout.split("\x1e"):
            parts = rec.strip().split("\x1f")
            if len(parts) >= 4:
                out.append({"kind": "commit", "title": parts[1], "body": parts[2], "closedAt": parts[3],
                            "url": "", "number": parts[0][:8], "repository": {"nameWithOwner": p.name}})
    return out


def filter_repos(items: list[dict], include: list[str], exclude: list[str]) -> list[dict]:
    def name(it):
        return ((it.get("repository") or {}).get("nameWithOwner") or "").lower()
    inc = [x.lower() for x in include]
    exc = [x.lower() for x in exclude]
    return [it for it in items
            if (not inc or any(x in name(it) for x in inc)) and not any(x in name(it) for x in exc)]


# ---------------------------------------------------------------- render

def repo_label(item: dict, hide_private: bool) -> str:
    repo = item.get("repository") or {}
    name = repo.get("nameWithOwner") or repo.get("name") or "repo"
    if hide_private and repo.get("isPrivate"):
        return "private repo"
    return name


def render(items: list[dict], since: str, until: str, hide_private: bool) -> str:
    by_repo: dict[str, list[dict]] = {}
    for it in items:
        by_repo.setdefault(repo_label(it, hide_private), []).append(it)
    kinds = {k: sum(1 for i in items if i.get("kind", "pr") == k) for k in KIND_LABEL}
    L = ["---", "type: brag-entry", f"period_start: {since}", f"period_end: {until}",
         f"items: {len(items)}", f"repos: {len(by_repo)}",
         *[f"{k}s: {v}" for k, v in kinds.items() if v],
         "status: raw  # run the brag-curator agent to curate",
         f"generator: friday_setup.py {__version__}", "---", "", f"# Shipped {since} → {until}", ""]
    for repo, group in sorted(by_repo.items()):
        L += [f"## {repo}", ""]
        for it in sorted(group, key=lambda x: x.get("closedAt", "")):
            private = hide_private and (it.get("repository") or {}).get("isPrivate")
            link = "" if private else (it.get("url") or "")
            label = KIND_LABEL.get(it.get("kind", "pr"), "Item")
            L += [f"### {redact((it.get('title') or '').strip())}",
                  f"- {label}: {(it.get('closedAt') or '')[:10]}" + (f" · [link]({link})" if link else ""),
                  "", clean_body(it.get("body", "")) or "_No description._", "",
                  "- Impact: _(what changed for users, the team or the business; add a number if you have one)_",
                  "- Skills: _(tools and practices this proves)_",
                  "- Portfolio artifact: _(which artifact this feeds, or 'new')_", ""]
    if not items:
        L.append("Nothing new in this window. Log a learning, a review you gave, or a doc you wrote instead.")
    return "\n".join(L)


# ---------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    where = ap.add_mutually_exclusive_group(required=True)
    where.add_argument("--portfolio", help="your portfolio repo (source of truth); raw pulls go to brag/inbox/")
    where.add_argument("--out", help="a plain folder outside any git repo (Drive-synced folder or Obsidian vault)")
    ap.add_argument("--promote", help="with --portfolio: move a curated inbox file into brag/entries/")
    ap.add_argument("--since", help="YYYY-MM-DD (default: last run, else 7 days ago)")
    ap.add_argument("--org", help="limit to one GitHub owner or org")
    ap.add_argument("--repo", nargs="*", default=[], help="only repos whose name contains any of these")
    ap.add_argument("--exclude-repo", nargs="*", default=[], help="skip repos whose name contains any of these")
    ap.add_argument("--limit", type=int, default=200, help="max results per search (GitHub caps at 1000)")
    ap.add_argument("--include-reviews", action="store_true", help="add merged PRs you reviewed")
    ap.add_argument("--include-issues", action="store_true", help="add issues you opened that were closed")
    ap.add_argument("--git-repos", nargs="*", default=[], help="read local repos with git log instead of gh")
    ap.add_argument("--author", help="author filter for --git-repos (default: each repo's git user.email)")
    ap.add_argument("--show-private", action="store_true", help="keep private repo names and links")
    ap.add_argument("--allow-repo", action="store_true", help="allow --out inside a git repository")
    ap.add_argument("--dry-run", action="store_true", help="print the file; write nothing, remember nothing")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    a = ap.parse_args(argv)

    if a.since:
        try:
            dt.date.fromisoformat(a.since)
        except ValueError:
            ap.error("--since must be YYYY-MM-DD")
    if a.promote and not a.portfolio:
        ap.error("--promote needs --portfolio")
    if a.portfolio:
        repo = pathlib.Path(a.portfolio).expanduser().resolve()
        if not repo.is_dir():
            print(f"{repo} is not a folder. Point --portfolio at your portfolio repo.", file=sys.stderr)
            return 2
        if a.promote:
            return promote(repo, pathlib.Path(a.promote).expanduser())
        if not (repo / "portfolio.json").exists():
            print(f"note: {repo} has no portfolio.json yet; copy templates/portfolio.json there.", file=sys.stderr)
        out = repo / "brag" / "inbox"
        if not a.dry_run:
            added = ensure_portfolio_ignores(repo)
            if added:
                print(f"Added to {repo / '.gitignore'}: {', '.join(added)}")
    else:
        out = pathlib.Path(a.out).expanduser().resolve()
    if not a.portfolio and inside_git_repo(out) and not a.allow_repo:
        print(f"Refusing to write into {out}: it is inside a git repository, so your brag file could end up "
              "on GitHub. Pick a folder outside any repo (a Drive-synced folder works well), or pass --allow-repo.",
              file=sys.stderr)
        return 2
    state = load_state(out)
    since = a.since or state.get("last_run") or (dt.date.today() - dt.timedelta(days=7)).isoformat()
    until = dt.date.today().isoformat()
    limit = max(1, min(a.limit, 1000))

    items: list[dict] = []
    failed: list[str] = []
    if a.git_repos:
        items += git_commits(a.git_repos, since, a.author)
    else:
        require_gh()
        sources = [("merged PRs", gh_prs)]
        if a.include_reviews:
            sources.append(("reviews", gh_reviews))
        if a.include_issues:
            sources.append(("issues", gh_issues))
        for label, fn in sources:
            try:
                items += fn(since, a.org, limit)
            except SourceError as e:
                failed.append(label)
                print(f"warning: couldn't pull {label}: {e}", file=sys.stderr)

    items = filter_repos(items, a.repo, a.exclude_repo)
    seen = set(state.get("seen", []))
    unique: dict[str, dict] = {}
    for it in items:
        k = item_key(it)
        if k not in seen and k not in unique:
            unique[k] = it
    items = list(unique.values())
    md = render(items, since, until, hide_private=not a.show_private)

    if a.dry_run:
        print(md)
        print(f"\n(dry run: {len(items)} new items since {since}; nothing written)", file=sys.stderr)
        return 1 if failed else 0

    out.mkdir(parents=True, exist_ok=True)
    f = out / f"{until}.md"
    if f.exists():
        f = out / f"{until}-{dt.datetime.now().strftime('%H%M%S')}.md"
    atomic_write(f, md)
    new_seen = (list(state.get("seen", [])) + list(unique))[-SEEN_CAP:]
    # Move the window forward only when every source succeeded, so a failed pull is retried next run.
    next_since = until if not failed else since
    atomic_write(out / STATE, json.dumps({"last_run": next_since, "seen": new_seen, "version": __version__}))
    print(f"Wrote {f} ({len(items)} new items since {since})")
    if failed:
        print(f"Some sources failed ({', '.join(failed)}); they'll be retried from {since} next run.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
