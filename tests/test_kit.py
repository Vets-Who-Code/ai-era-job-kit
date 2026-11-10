"""Offline tests for the kit. Network calls are stubbed with fixtures.
Run: python3 -m unittest discover -s tests -v   (from the kit root)
"""
import csv
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT / "scripts"))

from jobdata import bls, demand, docs, lexicon, onet, postings  # noqa: E402
import friday_setup  # noqa: E402
import funnel  # noqa: E402
import sync_check  # noqa: E402


class TestOnetParse(unittest.TestCase):
    def test_tech_skills_flags(self):
        rows = onet.parse_tsv((FIX / "technology_skills.tsv").read_text())
        o = onet.Onet(version="30_2")
        o._cache["Technology Skills.txt"] = rows
        ts = o.technology_skills("15-1252.00")
        py = next(t for t in ts if t["skill"] == "Python")
        self.assertTrue(py["hot"] and py["in_demand"])
        self.assertEqual(len(ts), 6)

    def test_missing_code_raises(self):
        o = onet.Onet(version="30_2")
        o._cache["Technology Skills.txt"] = onet.parse_tsv((FIX / "technology_skills.tsv").read_text())
        with self.assertRaises(Exception):
            o.technology_skills("99-9999.00")


class TestBls(unittest.TestCase):
    def test_parse_projections(self):
        rows = bls.parse_projections((FIX / "projections.html").read_text())
        sd = rows["15-1252"]
        self.assertEqual(sd["growth_pct_10yr"], 10.0)
        self.assertEqual(sd["annual_openings_thousands"], 50.0)
        self.assertEqual(sd["median_wage"], 100000.0)

    def test_soc6(self):
        self.assertEqual(bls.soc6("15-1252.00"), "15-1252")

    def test_fetch_failure_stops(self):
        with mock.patch.object(bls, "fetch", side_effect=bls.FetchError("blocked")):
            with self.assertRaises(bls.FetchError):
                bls.Bls().projections("15-1252.00")


class TestLexicon(unittest.TestCase):
    def test_no_false_java_from_javascript(self):
        found = lexicon.find_skills("Strong JavaScript skills", lexicon.CURATED)
        self.assertIn("JavaScript", found)
        self.assertNotIn("Java", found)

    def test_aliases(self):
        found = lexicon.find_skills("Postgres + pgvector, k8s, GitHub Actions", lexicon.CURATED)
        for s in ("PostgreSQL", "pgvector", "Kubernetes", "CI/CD"):
            self.assertIn(s, found)


class TestScoring(unittest.TestCase):
    def setUp(self):
        self.tech = onet.Onet(version="x")
        self.tech._cache["Technology Skills.txt"] = onet.parse_tsv((FIX / "technology_skills.tsv").read_text())
        self.rows = self.tech.technology_skills("15-1252.00")
        self.posts = postings.load_folder(FIX / "postings")

    def test_posting_skills_outrank_onet_only(self):
        d, _ = demand.build_demand(self.rows, self.posts, top=40)
        names = [x.skill for x in d]
        # LangGraph is not in this O*NET fixture but 2 of 3 postings ask for it.
        self.assertIn("LangGraph", names)
        self.assertLess(names.index("Python"), names.index("Kubernetes"))

    def test_score_without_postings_uses_onet(self):
        d, _ = demand.build_demand(self.rows, [], top=10)
        self.assertTrue(all(x.posting_share == 0 for x in d))
        self.assertTrue(d)


class TestScreenGrade(unittest.TestCase):
    """Per-posting Screen Grade, modeled on Workday HiredScore's documented A-D grades."""

    def setUp(self):
        import screen_grade
        self.sg = screen_grade
        self.quals = screen_grade.split_posting("Software Engineer, Platform",
                                                (FIX / "screen_posting.txt").read_text())
        self.resume = str(FIX / "screen_resume.txt")
        self.record = json.loads((FIX / "portfolio.json").read_text())

    def grades(self, met_ids, quotes=None):
        quotes = quotes or {}
        good = {"B1": "Software Engineer, Example Logistics, Jan 2022 - Present",
                "B2": "Designed PostgreSQL schemas and SQL reports used by 12 analysts",
                "B3": "Moved nightly batch jobs to AWS Lambda with Terraform",
                "B4": "Wrote the GitHub Actions CI/CD pipeline",
                "P1": "Docker, GitHub Actions, Kubernetes",
                "P2": "Built an evaluation harness for a retrieval assistant"}
        rows = []
        for q in self.quals["basic"] + self.quals["preferred"]:
            m = q["id"] in met_ids
            rows.append({"id": q["id"], "met": m, "evidence": quotes.get(q["id"], good.get(q["id"], "")) if m else ""})
        return {"title": {"resume_title": "Software Engineer"}, "industry": {"posting": "fintech", "evidence": ""},
                "grades": rows}

    def test_split_basic_preferred_and_knockouts(self):
        self.assertEqual(len(self.quals["basic"]), 4)
        self.assertEqual(len(self.quals["preferred"]), 3)
        kinds = {k["knockout"] for k in self.quals["knockouts"]}
        self.assertIn("work authorization", kinds)
        self.assertIn("minimum years", kinds)
        self.assertFalse(any("authorized" in q["text"] for q in self.quals["basic"]))

    def test_letters_follow_vendor_definitions(self):
        gl = self.sg.grade_letter
        self.assertEqual(gl(4, 4, 2, 3)[0], "A")   # all basic + most preferred
        self.assertEqual(gl(4, 4, 1, 3)[0], "B")   # all basic
        self.assertEqual(gl(3, 4, 3, 3)[0], "C")   # most, not all, basic
        self.assertEqual(gl(2, 4, 3, 3)[0], "D")   # half is not most
        self.assertEqual(gl(0, 4, 0, 3)[0], "D")

    def test_grade_with_portfolio_hit(self):
        r = self.sg.grade(self.resume, self.quals, self.grades({"B1", "B2", "B3", "B4", "P1"}), self.record)
        self.assertEqual(r["grade"], "B")
        self.assertEqual((r["basic"], r["preferred"]), ("4/4", "1/3"))
        p1 = next(x for x in r["rows"] if x["id"] == "P1")
        self.assertTrue(p1["skills_list_only"])
        p2 = next(x for x in r["rows"] if x["id"] == "P2")
        self.assertTrue(any("rag-eval-harness" in h for h in p2["portfolio_shows"]))
        self.assertIn("# Screen Grade: B", self.sg.report_md(r))

    def test_refuses_a_quote_not_on_the_resume(self):
        g = self.grades({"B1", "B2", "B3", "B4"}, {"B3": "Ran Kubernetes clusters on GCP for 5 years"})
        r = self.sg.grade(self.resume, self.quals, g, self.record)
        self.assertIn("refused", r)
        self.assertTrue(any("B3" in m for m in r["refused"]))

    def test_refuses_missing_grades(self):
        g = self.grades({"B1"})
        g["grades"] = g["grades"][:2]
        self.assertIn("refused", self.sg.grade(self.resume, self.quals, g, self.record))

    def test_parse_gate_gives_no_grade(self):
        with tempfile.TemporaryDirectory() as td:
            thin = pathlib.Path(td) / "thin.txt"
            thin.write_text("Jordan Sample\nPython developer\nSkills: Python, SQL, AWS\n")
            r = self.sg.grade(str(thin), self.quals, self.grades(set()), None)
        self.assertEqual(r["grade"], "No grade")

    def test_hes_and_years_checks(self):
        text = (FIX / "screen_resume.txt").read_text()
        rules = {f["rule"]: f["ok"] for f in self.sg.format_checks(text, self.sg.sections(text))}
        self.assertTrue(rules["No personal pronouns"])
        self.assertTrue(rules["Experience length says 5+ or 10+ only, never more than 10+"])
        bad = text.replace("10+ years", "12 years")
        rules = {f["rule"]: f["ok"] for f in self.sg.format_checks(bad, self.sg.sections(bad))}
        self.assertFalse(rules["Experience length says 5+ or 10+ only, never more than 10+"])

    def test_refuses_inside_a_git_repo(self):
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(["git", "init", "-q", td], check=True)
            res = pathlib.Path(td) / "resume.txt"
            res.write_text((FIX / "screen_resume.txt").read_text())
            q = pathlib.Path(td).parent / f"q-{pathlib.Path(td).name}.json"
            g = pathlib.Path(td).parent / f"g-{pathlib.Path(td).name}.json"
            q.write_text(json.dumps(self.quals))
            g.write_text(json.dumps(self.grades(set())))
            try:
                with self.assertRaises(SystemExit) as cm:
                    self.sg.main(["grade", "--resume", str(res), "--quals", str(q), "--grades", str(g)])
                self.assertEqual(cm.exception.code, 2)
            finally:
                q.unlink(); g.unlink()


class TestFunnel(unittest.TestCase):
    def test_lifecycle_and_report(self):
        with tempfile.TemporaryDirectory() as td:
            f = str(pathlib.Path(td) / "f.csv")
            funnel.main(["init", "--file", f])
            funnel.main(["add", "--file", f, "--company", "A", "--role", "AI Eng", "--channel", "referral",
                         "--artifact", "rag"])
            funnel.main(["add", "--file", f, "--company", "B", "--role", "AI Eng", "--channel", "cold"])
            funnel.main(["move", "--file", f, "--id", "1", "--stage", "offer"])
            funnel.main(["close", "--file", f, "--id", "2", "--status", "ghosted"])
            with open(f) as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual(rows[0]["status"], "offer")
            md = funnel.build_report(rows, None)
            self.assertIn("| referral | 1 |", md)
            self.assertIn("Portfolio effect", md)


class TestMarketSnapshotStopsOffline(unittest.TestCase):
    def test_cli_exits_3_when_onet_unreachable(self):
        import market_snapshot
        with mock.patch.object(onet, "fetch", side_effect=onet.FetchError("blocked")):
            rc = market_snapshot.main(["--roles", "web developer"])
        self.assertEqual(rc, 3)


class TestFunnelResumeVersions(unittest.TestCase):
    def test_by_resume_version_and_old_lane_column(self):
        with tempfile.TemporaryDirectory() as td:
            f = pathlib.Path(td) / "f.csv"
            # An older tracker that still has a "lane" column must keep working.
            f.write_text("id,date_applied,company,role,lane,channel,stage,stage_date,status,resume_version,"
                         "artifact_shared,url,lesson,notes\n"
                         "1,2026-10-01,A,Dev,ai,referral,screen,2026-10-02,active,web-v1,,,,\n")
            funnel.main(["add", "--file", str(f), "--company", "B", "--role", "Dev", "--channel", "recruiter",
                         "--resume-version", "data-v1"])
            with open(f) as fh:
                rows = list(csv.DictReader(fh))
            self.assertNotIn("lane", rows[0])
            md = funnel.build_report(rows, None)
            self.assertIn("## By resume version", md)
            self.assertIn("| web-v1 | 1 | 1 | 0 |", md)


class TestFridaySetup(unittest.TestCase):
    def test_redaction(self):
        t = friday_setup.redact("key ghp_" + "a" * 36 + " mail me@corp.com host db1.corp api_key=abc123 10.0.0.5")
        for leaked in ("ghp_", "me@corp.com", "db1.corp", "abc123", "10.0.0.5"):
            self.assertNotIn(leaked, t)

    def test_render_hides_private_links(self):
        items = [{"title": "Add evals", "url": "https://github.com/x/secret/pull/1", "body": "<!-- tpl -->Did it",
                  "closedAt": "2026-10-30T00:00:00Z", "repository": {"nameWithOwner": "x/secret", "isPrivate": True}}]
        md = friday_setup.render(items, "2026-10-24", "2026-10-31", hide_private=True)
        self.assertIn("private repo", md)
        self.assertNotIn("x/secret", md)
        self.assertNotIn("tpl", md)

    def test_git_mode_end_to_end(self):
        with tempfile.TemporaryDirectory() as td:
            repo = pathlib.Path(td) / "r"
            repo.mkdir()
            run = lambda *a: subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)
            run("init", "-q")
            run("-c", "user.email=t@t.io", "-c", "user.name=T", "commit", "--allow-empty", "-q", "-m", "Ship evals")
            out = pathlib.Path(td) / "brag"
            args = ["--out", str(out), "--git-repos", str(repo), "--since", "2000-01-01", "--author", "t@t.io"]
            self.assertEqual(friday_setup.main(args), 0)
            files = [p for p in out.glob("*.md")]
            self.assertEqual(len(files), 1)
            self.assertIn("Ship evals", files[0].read_text())
            # Second run logs nothing new: already-seen items are skipped.
            friday_setup.main(args)
            newest = max(out.glob("*.md"), key=lambda q: q.stat().st_mtime_ns).read_text()
            self.assertIn("items: 0", newest)

    def test_refuses_to_write_inside_a_repo(self):
        with tempfile.TemporaryDirectory() as td:
            (pathlib.Path(td) / ".git").mkdir()
            rc = friday_setup.main(["--out", str(pathlib.Path(td) / "brag"), "--git-repos", td])
            self.assertEqual(rc, 2)
            self.assertFalse((pathlib.Path(td) / "brag").exists())

    def test_gh_visibility_tags_private_and_failed_source_keeps_window(self):
        calls = []

        def fake_run(cmd, timeout=90):
            calls.append(cmd)
            if cmd[:3] == ["gh", "auth", "status"]:
                return ""
            if "issues" in cmd:
                raise friday_setup.SourceError("rate limited")
            vis = cmd[cmd.index("--visibility") + 1]
            if vis == "private":
                return json.dumps([{"title": "Secret thing", "url": "https://github.com/x/priv/pull/2",
                                    "body": "", "closedAt": "2026-10-30T00:00:00Z", "number": 2,
                                    "repository": {"nameWithOwner": "x/priv"}}])
            return "[]"

        with tempfile.TemporaryDirectory() as td, \
                mock.patch.object(friday_setup, "_run", side_effect=fake_run), \
                mock.patch.object(friday_setup.shutil, "which", return_value="/usr/bin/gh"):
            out = pathlib.Path(td) / "brag"
            rc = friday_setup.main(["--out", str(out), "--since", "2026-10-24", "--include-issues"])
            self.assertEqual(rc, 1)
            md = next(out.glob("*.md")).read_text()
            self.assertIn("private repo", md)
            self.assertNotIn("x/priv", md)
            state = json.loads((out / friday_setup.STATE).read_text())
            self.assertEqual(state["last_run"], "2026-10-24")


class TestPortfolioAsSourceOfTruth(unittest.TestCase):
    def _repo(self, td):
        repo = pathlib.Path(td) / "portfolio"
        repo.mkdir()
        (repo / ".git").mkdir()
        (repo / "portfolio.json").write_text("{}")
        return repo

    def test_portfolio_mode_writes_to_ignored_inbox(self):
        with tempfile.TemporaryDirectory() as td:
            repo = self._repo(td)
            src = pathlib.Path(td) / "src"
            src.mkdir()
            run = lambda *a: subprocess.run(["git", "-C", str(src), *a], check=True, capture_output=True)
            run("init", "-q")
            run("-c", "user.email=t@t.io", "-c", "user.name=T", "commit", "--allow-empty", "-q", "-m", "Add evals")
            rc = friday_setup.main(["--portfolio", str(repo), "--git-repos", str(src), "--since", "2000-01-01",
                                    "--author", "t@t.io"])
            self.assertEqual(rc, 0)
            self.assertEqual(len(list((repo / "brag" / "inbox").glob("*.md"))), 1)
            gi = (repo / ".gitignore").read_text()
            self.assertIn("brag/inbox/", gi)
            self.assertIn(friday_setup.STATE, gi)

    def test_promote_gates_raw_and_unsafe_files(self):
        with tempfile.TemporaryDirectory() as td:
            repo = self._repo(td)
            inbox = repo / "brag" / "inbox"
            inbox.mkdir(parents=True)
            raw = inbox / "2026-10-31.md"
            raw.write_text("---\nstatus: raw\n---\n- Impact: _(what changed for users)_\n")
            self.assertEqual(friday_setup.main(["--portfolio", str(repo), "--promote", str(raw)]), 2)
            leak = inbox / "2026-10-30.md"
            leak.write_text("---\nstatus: curated\n---\nShipped search, ping me at me@corp.com\n")
            self.assertEqual(friday_setup.main(["--portfolio", str(repo), "--promote", str(leak)]), 2)
            good = inbox / "2026-10-29.md"
            good.write_text("---\nstatus: curated\n---\nCut search latency 40% for 2,000 users.\n")
            self.assertEqual(friday_setup.main(["--portfolio", str(repo), "--promote", "brag/inbox/2026-10-29.md"]), 0)
            self.assertTrue((repo / "brag" / "entries" / "2026-10-29.md").exists())
            self.assertFalse(good.exists())

    def test_sync_check_finds_mismatches_offline(self):
        record = {"profile": {"target_role": "AI Engineer"},
                  "links": {"site": "https://pat.dev"},
                  "experience": [{"title": "Software Developer", "org": "Acme"}],
                  "artifacts": [{"name": "rag-eval-harness", "depth": 3, "url": "https://pat.dev/rag",
                                 "skills": ["Python", "RAG", "Evals", "FastAPI", "LangGraph"]},
                                {"name": "todo-local", "depth": 1, "skills": ["React"]}]}
        resume = docs.read_text(str(FIX / "candidate.txt")) + "\n15 years of experience\n"
        linkedin = "AI Engineer. Featured: rag eval harness https://pat.dev/rag. Software Developer at Acme."
        found = sync_check.check(record, resume, linkedin, None)
        bad = {(f["area"], f["item"], f["surface"]) for f in found if not f["ok"]}
        self.assertNotIn(("Headline", "AI Engineer", "resume"), bad)
        self.assertIn(("Artifacts", "rag-eval-harness", "resume"), bad)
        self.assertNotIn(("Artifacts", "rag-eval-harness", "LinkedIn"), bad)
        self.assertNotIn(("Artifacts", "todo-local", "resume"), {(a, i, s) for a, i, s in bad})
        self.assertIn(("Experience", "Software Developer at Acme", "resume"), bad)
        self.assertIn(("Skills", "Kubernetes", "resume"), bad)
        self.assertNotIn(("Skills", "LangGraph", "resume"), bad)
        self.assertIn(("Years", "15 years", "resume"), bad)
        self.assertIn("## Fix these", sync_check.report(found, []))


class TestScoringChain(unittest.TestCase):
    """The 7-step chain: resume, LinkedIn, GitHub, portfolio, composite, plan, rebuild. All offline."""

    def setUp(self):
        import resume_score
        tech = onet.Onet(version="x")
        tech._cache["Technology Skills.txt"] = onet.parse_tsv((FIX / "technology_skills.tsv").read_text())
        self.rows = tech.technology_skills("15-1252.00")
        self.posts = postings.load_folder(FIX / "postings")
        self.rs = resume_score.score(docs.read_text(str(FIX / "screen_resume.txt")), self.rows, self.posts, now=2026)
        self.td = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self.td.name)
        (self.tmp / "rs.json").write_text(json.dumps(self.rs))
        from jobdata import market
        self.mk = market
        self.market = market.load(str(self.tmp / "rs.json"))
        self.record = json.loads((ROOT / "templates" / "portfolio.json").read_text())

    def tearDown(self):
        self.td.cleanup()

    def assertSchema(self, r, surface):
        self.assertEqual(r["surface"], surface)
        self.assertTrue(0 <= r["score"] <= 100)
        for c in r["checks"]:
            self.assertTrue({"section", "check", "pass", "detail", "weight", "fix"} <= set(c))
            self.assertEqual(c["fix"] == "", c["pass"])

    def test_step1_resume_score_and_parse_gate(self):
        import resume_score
        self.assertSchema(self.rs, "resume")
        self.assertTrue(self.rs["skills"])
        self.assertTrue(all(k["grade"] in resume_score.GRADES for k in self.rs["skills"]))
        bad = resume_score.score(docs.read_text(str(FIX / "candidate.txt")), self.rows, self.posts, now=2026)
        self.assertIsNone(bad["score"])  # no score until the format parses

    def test_market_file_is_required_or_live(self):
        with self.assertRaises(ValueError):
            self.mk.load(None, None)
        (self.tmp / "empty.json").write_text("{}")
        with self.assertRaises(ValueError):
            self.mk.load(str(self.tmp / "empty.json"))
        share, found, missing = self.mk.coverage("Python and Docker", self.market, top=10)
        self.assertTrue(0 <= share <= 1)
        self.assertEqual(len(found) + len(missing), min(10, len(self.market["skills"])))

    def test_step2_linkedin_score(self):
        import linkedin_score
        text = (ROOT / "templates" / "linkedin-profile.txt").read_text()
        r = linkedin_score.score(text, self.market, self.record)
        self.assertSchema(r, "linkedin")
        sec = linkedin_score.split_profile(text)
        self.assertIn("Software Engineer", sec["headline"])
        self.assertTrue(all(all(x.startswith("LinkedIn ") for x in v) for v in r["skill_evidence"].values()))
        empty = linkedin_score.score("Headline: Hi", self.market, self.record)
        self.assertLess(empty["score"], r["score"])

    def test_step3_github_score_stubbed(self):
        import base64
        import github_score
        readme = base64.b64encode(("# rag-eval-harness\n" + "Why: we chose pgvector. Python FastAPI RAG Evals Docker. " * 40).encode()).decode()
        pages = {
            "/users/pat": {"bio": "I build Python AI tools", "blog": "https://yourname.dev"},
            "/users/pat/repos?per_page=100&sort=pushed": [
                {"name": "rag-eval-harness", "fork": False, "pushed_at": "2026-10-30T00:00:00Z", "homepage": "https://yourname.dev/rag",
                 "description": "Policy QA with evals", "topics": ["rag", "python"], "language": "Python", "license": {"spdx_id": "MIT"}},
                {"name": "old-fork", "fork": True, "pushed_at": "2020-01-01T00:00:00Z"}],
            "/repos/pat/pat/readme": {"content": readme},
            "/repos/pat/rag-eval-harness/readme": {"content": readme},
            "/repos/pat/rag-eval-harness/contents/": [{"name": "tests"}, {"name": ".github"}, {"name": "app.py"}],
            "/repos/pat/rag-eval-harness/contents/.github/workflows": [{"name": "ci.yml"}],
        }

        class Fake(github_score.GitHub):
            def get(self, path):
                self.calls += 1
                if path not in pages:
                    raise github_score.FetchError(f"404 {path}")
                return pages[path]

        import datetime as dt
        r = github_score.score(Fake(), "pat", ["rag-eval-harness"], self.market, self.record, today=dt.date(2026, 11, 6))
        self.assertSchema(r, "github")
        ok = {c["check"]: c["pass"] for c in r["checks"] if c["section"] == "rag-eval-harness"}
        self.assertTrue(ok["Tests in the repo"] and ok["CI workflow"] and ok["Live demo link"])
        self.assertTrue(all(c["pass"] for c in r["checks"] if c["check"] == "Portfolio artifacts are the pinned repos"))
        r2 = github_score.score(Fake(), "pat", [], self.market, None, today=dt.date(2026, 11, 6))
        self.assertIn("Pins unknown", r2["note"])
        self.assertTrue(any("GitHub rag-eval-harness" in v for v in r["skill_evidence"].values()))  # pushed this year
        stale = github_score.score(Fake(), "pat", ["rag-eval-harness"], self.market, None, today=dt.date(2028, 6, 1))
        self.assertEqual(stale["skill_evidence"], {})  # no push in a year, no activity proof
        self.assertEqual(r2["repos"], ["rag-eval-harness"])  # forks skipped

    def test_proven_needs_github_or_linkedin(self):
        import resume_score
        import scorecard
        on_paper = [k for k in self.rs["skills"] if k["text_grade"] == "proven"]
        self.assertTrue(on_paper)
        self.assertFalse(self.rs["corroborated"])
        self.assertTrue(all(k["grade"] == "applied" for k in on_paper))  # a number alone isn't proof
        sk = on_paper[0]["skill"]
        gh = {"surface": "github", "score": 80, "checks": [], "skill_evidence": {sk: ["GitHub rag-eval-harness"]}}
        li = {"surface": "linkedin", "score": 80, "checks": [], "skill_evidence": {sk: ["LinkedIn Experience"]}}
        ev = resume_score.merge_evidence(li, gh)
        self.assertEqual(ev[sk], ["LinkedIn Experience", "GitHub rag-eval-harness"])
        r = resume_score.corroborate(json.loads(json.dumps(self.rs)), ev)
        self.assertEqual({k["skill"]: k["grade"] for k in r["skills"]}[sk], "proven")
        self.assertGreater(r["score"], self.rs["score"])
        listed = [k for k in self.rs["skills"] if k["text_grade"] == "listed"]
        if listed:  # outside proof never lifts a skill the resume only lists
            r2 = resume_score.corroborate(json.loads(json.dumps(self.rs)), {listed[0]["skill"]: ["GitHub x"]})
            self.assertEqual({k["skill"]: k["grade"] for k in r2["skills"]}[listed[0]["skill"]], "listed")
        c = scorecard.composite({"resume": dict(self.rs), "github": gh, "linkedin": li})
        self.assertEqual(c["inputs"]["resume"]["score"], r["score"])  # the composite applies the same rule
        self.assertEqual(self.rs["skills"][0].get("backed_by"), [])  # and doesn't change the step 1 file

    def test_step5_two_reads_and_resume_gate(self):
        import scorecard
        self.assertEqual(scorecard.READS["machine"], {"resume": 40, "linkedin": 35, "github": 15, "portfolio": 10})
        self.assertEqual(scorecard.READS["human"], {"portfolio": 35, "github": 30, "resume": 20, "linkedin": 15})
        self.assertEqual(scorecard.RESUME_GATE, 70)
        s = {"resume": {"surface": "resume", "score": 60, "checks": [], "skills": []},
             "linkedin": {"surface": "linkedin", "score": 80, "checks": []}}
        c = scorecard.composite(s)
        self.assertEqual(c["machine"]["score"], 69)  # (40*60 + 35*80) / 75, reweighted
        self.assertEqual(c["human"]["score"], 69)    # (20*60 + 15*80) / 35
        self.assertTrue(c["partial"])
        self.assertEqual(set(c["missing"]), {"github", "portfolio"})
        self.assertFalse(c["gate"]["passed"])        # 60 is under the gate, whatever the totals
        self.assertTrue(scorecard.composite(s, gate=55)["gate"]["passed"])
        full = dict(s, github={"surface": "github", "score": 100, "checks": []},
                    portfolio={"surface": "portfolio", "score": 100, "checks": []})
        cf = scorecard.composite(full)
        self.assertEqual((cf["machine"]["score"], cf["human"]["score"]), (77, 89))
        self.assertFalse(cf["gate"]["passed"])       # high totals don't clear a weak resume
        w = {"machine": scorecard.parse_weights("resume=75,linkedin=25", "machine"), "human": scorecard.parse_weights(None, "human")}
        self.assertEqual(scorecard.composite(s, w)["machine"]["score"], 65)
        with self.assertRaises(ValueError):
            scorecard.parse_weights("twitter=10", "human")
        blocked = scorecard.composite({"resume": {"surface": "resume", "score": None}})
        self.assertIsNone(blocked["machine"]["score"])
        self.assertEqual(blocked["blocked"], ["resume"])
        self.assertFalse(blocked["gate"]["passed"])
        self.assertIn("parse gate", blocked["gate"]["note"])
        self.assertIsNone(scorecard.composite({"linkedin": s["linkedin"]})["gate"]["passed"])

    def test_step6_plan_ranks_by_points_left(self):
        import scorecard
        s = {"resume": dict(self.rs),
             "portfolio": {"surface": "portfolio", "score": 90, "checks": [
                 {"section": "Proof", "check": "Live demo", "pass": False, "detail": "", "weight": 2, "fix": "Portfolio: add a live demo."}]}}
        p = scorecard.plan(scorecard.composite(s))
        scored = [x for x in p["steps"] if x["status"] == "scored"]
        self.assertEqual(scored[0]["surface"], "resume")  # gate-failed resume first, or the biggest gap
        p2 = scorecard.plan(scorecard.composite({"resume": {"surface": "resume", "score": 95, "checks": [], "skills": []},
                                                 "portfolio": {"surface": "portfolio", "score": 50, "checks": []}}))
        self.assertEqual([x["surface"] for x in p2["steps"] if x["status"] == "scored"], ["portfolio", "resume"])
        p3 = scorecard.plan(scorecard.composite({"resume": {"surface": "resume", "score": 65, "checks": [], "skills": []},
                                                 "portfolio": {"surface": "portfolio", "score": 10, "checks": []}}))
        self.assertEqual(p3["steps"][0]["surface"], "resume")  # gate beats a bigger portfolio gap
        self.assertTrue(p3["steps"][0]["gate"])
        self.assertEqual({x["surface"]: x["skill"] for x in p["steps"]}["resume"], "resume-rebuilder")
        self.assertIn("Portfolio: add a live demo.", [f for x in p["steps"] for f in x["fixes"]])
        md = sync_check.report([{"area": "Headline", "item": "AI Engineer", "surface": "resume", "ok": False, "fix": "Say it."}], [])
        self.assertEqual(scorecard.sync_summary(md)["fixes"], ["Headline (resume): Say it."])
        ok = sync_check.report([{"area": "Headline", "item": "x", "surface": "resume", "ok": True, "fix": ""}], [])
        self.assertTrue(scorecard.sync_summary(ok)["in_sync"])

    def test_step7_rebuild_never_invents(self):
        import resume_rebuild
        brag = self.tmp / "brag"
        brag.mkdir()
        (brag / "2026-10-31.md").write_text("---\nstatus: curated\n---\n## search\n### Cut search latency\n"
                                            "- Impact: 40% faster for 300 users\n- Skills: Redis\n- Portfolio artifact: none\n")
        (brag / "2026-11-01.md").write_text("---\nstatus: raw\n---\n## x\n### Raw item\n- Impact: 9\n")
        record = dict(self.record)
        record["experience"] = [dict(self.record["experience"][0], highlights=["brag/entries/2026-10-31.md#cut-search-latency"])]
        market, vocab = resume_rebuild.load_market(str(self.tmp / "rs.json"))
        r = resume_rebuild.rebuild(record, resume_rebuild.read_brag(str(brag)), market, vocab)
        self.assertIn("- Cut search latency: 40% faster for 300 users", r["resume"])
        self.assertNotIn("Raw item", r["resume"])
        self.assertIn("[ask: email]", r["asks"])
        listed = set(self.record["artifacts"][0]["skills"]) | {"Redis"}
        on = lexicon.find_skills(r["resume"], vocab)
        self.assertTrue(on <= {s for s in on if s in listed or s.lower() in r["resume"].lower()})
        for s in r["prove_first"]:
            self.assertNotIn(s, lexicon.find_skills(r["resume"].split("SKILLS")[1], vocab))
        c = resume_rebuild.check(r["resume"])
        self.assertFalse(c["pass"])  # placeholders and no email yet
        self.assertTrue(resume_rebuild.check(docs.read_text(str(FIX / "screen_resume.txt")))["checks"])

    def test_step7_refuses_out_path_in_git(self):
        import resume_rebuild
        repo = self.tmp / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        rc = resume_rebuild.main(["--portfolio", str(ROOT / "templates" / "portfolio.json"), "--out", str(repo / "r.txt")])
        self.assertEqual(rc, 2)
        self.assertFalse((repo / "r.txt").exists())


if __name__ == "__main__":
    unittest.main()


class TestDeckM2Decode(unittest.TestCase):
    def test_three_mentions_is_critical(self):
        text = ("Requirements\n- Python services in production\n- Python and SQL\n"
                "Nice to have\n- Python tooling, Kubernetes\n")
        import screen_grade
        q = screen_grade.split_posting("Eng", text)
        d = {x["skill"]: x for x in q["decode"]}
        self.assertTrue(d["Python"]["critical"])
        self.assertEqual(d["Python"]["tier"], "required")
        self.assertFalse(d["Kubernetes"]["critical"])
        self.assertEqual(d["Kubernetes"]["tier"], "preferred")
        self.assertEqual(q["decode"][0]["skill"], "Python")


class TestDeckM7Funnel(unittest.TestCase):
    def _rows(self, f):
        with open(f) as fh:
            return list(csv.DictReader(fh))

    def test_columns_postmortem_and_break_point(self):
        with tempfile.TemporaryDirectory() as td:
            f = str(pathlib.Path(td) / "f.csv")
            funnel.main(["init", "--file", f])
            for i in range(10):
                funnel.main(["add", "--file", f, "--company", f"C{i}", "--role", "Dev", "--source", "job-board",
                             "--next-action", "follow up", "--follow-up", "2000-01-01"])
            funnel.main(["close", "--file", f, "--id", "1", "--status", "rejected"])
            funnel.main(["postmortem", "--file", f, "--id", "1", "--cause", "no AWS proof",
                         "--fix", "AWS bullet with a number", "--layer", "resume"])
            rows = self._rows(f)
            for col in ("next_action", "follow_up", "pm_cause", "pm_fix", "pm_layer"):
                self.assertIn(col, rows[0])
            self.assertEqual(rows[0]["pm_layer"], "resume")
            md = funnel.build_report(rows, None)
            self.assertIn("No screens -> fix the **resume** layer", md)
            self.assertIn("Follow-ups due: 9", md)
            self.assertIn("no AWS proof -> fix: AWS bullet with a number [resume]", md)

    def test_diagnose_layers(self):
        self.assertEqual(funnel.diagnose(12, 0, 0, 0)[1], "resume")
        self.assertEqual(funnel.diagnose(12, 4, 0, 0)[1], "interview")
        self.assertEqual(funnel.diagnose(12, 5, 2, 0)[1], "defense")
        self.assertIsNone(funnel.diagnose(12, 5, 2, 1))

    def test_72_hour_rule(self):
        import datetime as dt
        rows = [{"id": "1", "company": "A", "role": "Dev", "channel": "cold", "stage": "applied",
                 "stage_date": "2026-11-01", "status": "rejected", "date_applied": "2026-11-01",
                 "pm_date": "2026-11-02T09:00:00", "pm_fix": "new headline", "pm_layer": "resume"}]
        md = funnel.build_report(rows, None, at=dt.datetime(2026, 11, 6))
        self.assertIn("no upward movement: it was opinion", md)
        rows.append(dict(rows[0], id="2", stage="screen", stage_date="2026-11-03", pm_fix="", pm_date=""))
        md = funnel.build_report(rows, None, at=dt.datetime(2026, 11, 6))
        self.assertIn("upward movement, keep it", md)
