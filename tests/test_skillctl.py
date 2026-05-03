"""Tests for scripts/skillctl.py — stdlib unittest, no third-party deps.

Run with:
    python3 -m unittest tests.test_skillctl
or:
    python3 tests/test_skillctl.py
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


# Add scripts/ to path before import so the module can be exercised in place.
HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO / "scripts"))
import skillctl  # noqa: E402


def _write_skill(repo: Path, name: str, *, version: int = 1, description: str = "x") -> Path:
    sd = repo / name
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "SKILL.md").write_text(
        textwrap.dedent(
            f"""\
            ---
            name: {name}
            version: {version}
            description: {description}
            triggers:
              - foo
              - bar
            ---

            # {name}

            body.
            """
        ),
        encoding="utf-8",
    )
    return sd


class _SandboxBase(unittest.TestCase):
    """Spin up a tmp 'repo' + tmp claude/codex/hermes homes for each test.

    The skillctl module reads roots via env vars, and ``repo_root()`` reads
    the script's parent. We monkey-patch ``skillctl.repo_root`` for each
    test to point at the tmp repo; env vars take care of the targets.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)

        self.repo = root / "sincerity-skills"
        self.repo.mkdir()
        # Pretend scripts/ exists; doctor() walks here.
        (self.repo / "scripts").mkdir()

        self.claude = root / "claude_home"
        self.codex = root / "codex_home"
        self.hermes = root / "hermes_home"
        for p in (self.claude, self.codex, self.hermes):
            p.mkdir()
        # default Hermes skills root + a couple profiles
        (self.hermes / "skills").mkdir()
        (self.hermes / "profiles").mkdir()
        (self.hermes / "profiles" / "alpha").mkdir()
        (self.hermes / "profiles" / "beta").mkdir()

        env_patcher = mock.patch.dict(
            os.environ,
            {
                "SKILLCTL_CLAUDE_HOME": str(self.claude),
                "SKILLCTL_CODEX_HOME": str(self.codex),
                "SKILLCTL_HERMES_HOME": str(self.hermes),
            },
            clear=False,
        )
        env_patcher.start()
        self.addCleanup(env_patcher.stop)

        repo_patcher = mock.patch.object(skillctl, "repo_root", return_value=self.repo)
        repo_patcher.start()
        self.addCleanup(repo_patcher.stop)

        # Two skills available by default for most tests
        _write_skill(self.repo, "alpha-skill")
        _write_skill(self.repo, "beta-skill")

    # ── helpers ──
    def run_cli(self, *argv: str) -> tuple[int, str]:
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                rc = skillctl.main(list(argv))
        except SystemExit as e:
            # argparse may exit with non-int code on usage errors — keep them.
            rc = int(e.code) if isinstance(e.code, int) else 2
        return rc, buf.getvalue()


# ---------------------------------------------------------------------------
# Frontmatter parser
# ---------------------------------------------------------------------------


class TestFrontmatter(unittest.TestCase):
    def test_simple(self) -> None:
        text = textwrap.dedent("""\
            ---
            name: foo
            version: 1
            description: hello world
            ---

            body
            """)
        out = skillctl.parse_frontmatter(text)
        self.assertEqual(out["name"], "foo")
        self.assertEqual(out["version"], "1")
        self.assertEqual(out["description"], "hello world")

    def test_list_value(self) -> None:
        text = textwrap.dedent("""\
            ---
            name: foo
            triggers:
              - one
              - two
              - "three with spaces"
            ---

            body
            """)
        out = skillctl.parse_frontmatter(text)
        self.assertEqual(out["triggers"], ["one", "two", "three with spaces"])

    def test_quoted_value(self) -> None:
        text = '---\nname: "foo"\ndescription: \'hi\'\n---\n\n'
        out = skillctl.parse_frontmatter(text)
        self.assertEqual(out["name"], "foo")
        self.assertEqual(out["description"], "hi")

    def test_missing_frontmatter(self) -> None:
        with self.assertRaises(ValueError):
            skillctl.parse_frontmatter("# just a heading\n\nno frontmatter\n")

    def test_orphan_list_item(self) -> None:
        text = "---\n  - dangling\n---\n"
        with self.assertRaises(ValueError):
            skillctl.parse_frontmatter(text)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


class TestDiscovery(_SandboxBase):
    def test_finds_skills_with_skill_md(self) -> None:
        names = [s.name for s in skillctl.discover_skills()]
        self.assertEqual(names, ["alpha-skill", "beta-skill"])

    def test_skips_dotfiles_and_scripts_and_tests(self) -> None:
        (self.repo / ".git").mkdir()
        (self.repo / "tests").mkdir()
        (self.repo / "tests" / "SKILL.md").write_text("---\nname: tests\ndescription: x\n---\n")
        (self.repo / ".hidden").mkdir()
        (self.repo / ".hidden" / "SKILL.md").write_text("---\nname: hidden\ndescription: x\n---\n")
        names = [s.name for s in skillctl.discover_skills()]
        self.assertEqual(names, ["alpha-skill", "beta-skill"])

    def test_skips_dirs_without_skill_md(self) -> None:
        (self.repo / "not-a-skill").mkdir()
        names = [s.name for s in skillctl.discover_skills()]
        self.assertNotIn("not-a-skill", names)


# ---------------------------------------------------------------------------
# Target resolution
# ---------------------------------------------------------------------------


class TestTargetResolution(_SandboxBase):
    def test_claude_codex(self) -> None:
        t = skillctl.resolve_target("claude")[0]
        self.assertEqual(t.slug, "claude")
        self.assertEqual(t.skills_dir, self.claude / "skills")
        t = skillctl.resolve_target("codex")[0]
        self.assertEqual(t.skills_dir, self.codex / "skills")

    def test_hermes_default(self) -> None:
        t = skillctl.resolve_target("hermes:default")[0]
        self.assertEqual(t.skills_dir, self.hermes / "skills")

    def test_hermes_named_profile(self) -> None:
        t = skillctl.resolve_target("hermes:alpha")[0]
        self.assertEqual(t.skills_dir, self.hermes / "profiles" / "alpha" / "skills")

    def test_hermes_unknown_profile(self) -> None:
        with self.assertRaises(SystemExit) as cm:
            skillctl.resolve_target("hermes:nope")
        self.assertIn("not found", str(cm.exception))
        self.assertIn("alpha", str(cm.exception))

    def test_hermes_glob(self) -> None:
        targets = skillctl.resolve_target("hermes:*")
        slugs = [t.slug for t in targets]
        self.assertEqual(set(slugs), {"hermes:default", "hermes:alpha", "hermes:beta"})

    def test_bare_hermes_rejected(self) -> None:
        with self.assertRaises(SystemExit) as cm:
            skillctl.resolve_target("hermes")
        msg = str(cm.exception)
        self.assertIn("ambiguous", msg)
        self.assertIn("hermes:alpha", msg)

    def test_unknown_slug(self) -> None:
        with self.assertRaises(SystemExit) as cm:
            skillctl.resolve_target("vscode")
        self.assertIn("unknown target", str(cm.exception))


# ---------------------------------------------------------------------------
# Deploy / undeploy
# ---------------------------------------------------------------------------


class TestDeployUndeploy(_SandboxBase):
    def test_deploy_creates_symlink(self) -> None:
        rc, out = self.run_cli("deploy", "alpha-skill", "--target", "claude")
        self.assertEqual(rc, 0, out)
        link = self.claude / "skills" / "alpha-skill"
        self.assertTrue(link.is_symlink())
        self.assertEqual(link.resolve(), (self.repo / "alpha-skill").resolve())

    def test_deploy_idempotent(self) -> None:
        self.run_cli("deploy", "alpha-skill", "--target", "claude")
        rc, out = self.run_cli("deploy", "alpha-skill", "--target", "claude")
        self.assertEqual(rc, 0, out)
        self.assertIn("already linked", out)

    def test_deploy_creates_target_skills_dir(self) -> None:
        # Drop the pre-created hermes/skills to test auto-create
        target_skills = self.hermes / "skills"
        for child in target_skills.iterdir():
            child.unlink()
        target_skills.rmdir()
        rc, _ = self.run_cli("deploy", "alpha-skill", "--target", "hermes:default")
        self.assertEqual(rc, 0)
        self.assertTrue(target_skills.is_dir())
        self.assertTrue((target_skills / "alpha-skill").is_symlink())

    def test_deploy_refuses_real_directory(self) -> None:
        (self.claude / "skills" / "alpha-skill").mkdir(parents=True)
        rc, out = self.run_cli("deploy", "alpha-skill", "--target", "claude")
        self.assertEqual(rc, 1)
        self.assertIn("real directory", out)
        # Ensure we did NOT touch the real dir
        self.assertTrue((self.claude / "skills" / "alpha-skill").is_dir())
        self.assertFalse((self.claude / "skills" / "alpha-skill").is_symlink())

    def test_deploy_skips_mismatched_symlink_without_force(self) -> None:
        elsewhere = self.repo / "alpha-skill"  # real path that exists
        bogus_target = self.repo / "beta-skill"
        link = self.claude / "skills" / "alpha-skill"
        (self.claude / "skills").mkdir(parents=True, exist_ok=True)
        link.symlink_to(bogus_target)
        rc, out = self.run_cli("deploy", "alpha-skill", "--target", "claude")
        self.assertEqual(rc, 1)
        self.assertIn("different symlink", out)
        # symlink unchanged
        self.assertEqual(link.resolve(), bogus_target.resolve())
        # Now with --force
        rc, out = self.run_cli("deploy", "alpha-skill", "--target", "claude", "--force")
        self.assertEqual(rc, 0)
        self.assertEqual(link.resolve(), elsewhere.resolve())

    def test_deploy_replaces_broken_symlink(self) -> None:
        link = self.claude / "skills" / "alpha-skill"
        (self.claude / "skills").mkdir(parents=True, exist_ok=True)
        link.symlink_to(self.repo / "ghost-skill")  # nonexistent
        rc, out = self.run_cli("deploy", "alpha-skill", "--target", "claude")
        self.assertEqual(rc, 0)
        self.assertEqual(link.resolve(), (self.repo / "alpha-skill").resolve())

    def test_deploy_all_to_multiple_targets(self) -> None:
        rc, out = self.run_cli(
            "deploy", "--all",
            "--target", "claude", "--target", "codex", "--target", "hermes:alpha",
        )
        self.assertEqual(rc, 0, out)
        for tdir in (
            self.claude / "skills",
            self.codex / "skills",
            self.hermes / "profiles" / "alpha" / "skills",
        ):
            self.assertTrue((tdir / "alpha-skill").is_symlink())
            self.assertTrue((tdir / "beta-skill").is_symlink())

    def test_deploy_to_glob_targets_every_profile(self) -> None:
        rc, _ = self.run_cli("deploy", "alpha-skill", "--target", "hermes:*")
        self.assertEqual(rc, 0)
        for prof in ("default", "alpha", "beta"):
            link = (
                self.hermes / "skills" / "alpha-skill"
                if prof == "default"
                else self.hermes / "profiles" / prof / "skills" / "alpha-skill"
            )
            self.assertTrue(link.is_symlink(), f"missing on {prof}")

    def test_unknown_skill_errors(self) -> None:
        rc, _ = self.run_cli("deploy", "ghost", "--target", "claude")
        self.assertEqual(rc, 2)

    def test_no_target_errors(self) -> None:
        rc, _ = self.run_cli("deploy", "alpha-skill")
        self.assertEqual(rc, 2)

    def test_undeploy_removes_symlink(self) -> None:
        self.run_cli("deploy", "alpha-skill", "--target", "claude")
        rc, out = self.run_cli("undeploy", "alpha-skill", "--target", "claude")
        self.assertEqual(rc, 0)
        self.assertIn("removed", out)
        self.assertFalse((self.claude / "skills" / "alpha-skill").exists())

    def test_undeploy_ignores_absent(self) -> None:
        rc, out = self.run_cli("undeploy", "alpha-skill", "--target", "claude")
        self.assertEqual(rc, 0)
        self.assertIn("absent", out)

    def test_undeploy_skips_real_directory_without_force(self) -> None:
        (self.claude / "skills" / "alpha-skill").mkdir(parents=True)
        rc, out = self.run_cli("undeploy", "alpha-skill", "--target", "claude")
        self.assertEqual(rc, 0)  # not-an-error on its own; just skipped
        self.assertIn("skipped", out)
        self.assertTrue((self.claude / "skills" / "alpha-skill").is_dir())


# ---------------------------------------------------------------------------
# Status / list / targets
# ---------------------------------------------------------------------------


class TestStatusListTargets(_SandboxBase):
    def test_list_json(self) -> None:
        rc, out = self.run_cli("list", "--json")
        self.assertEqual(rc, 0)
        names = [r["name"] for r in json.loads(out)]
        self.assertEqual(sorted(names), ["alpha-skill", "beta-skill"])

    def test_targets_includes_profiles(self) -> None:
        rc, out = self.run_cli("targets", "--json")
        self.assertEqual(rc, 0)
        slugs = [r["slug"] for r in json.loads(out)]
        # claude/codex/hermes:default + 2 profiles
        self.assertEqual(
            set(slugs),
            {"claude", "codex", "hermes:default", "hermes:alpha", "hermes:beta"},
        )

    def test_status_matrix_after_partial_deploy(self) -> None:
        self.run_cli("deploy", "alpha-skill", "--target", "claude")
        rc, out = self.run_cli("status", "--json")
        self.assertEqual(rc, 0)
        rows = {r["skill"]: r["targets"] for r in json.loads(out)}
        self.assertEqual(rows["alpha-skill"]["claude"], "matches")
        self.assertEqual(rows["alpha-skill"]["codex"], "absent")
        self.assertEqual(rows["beta-skill"]["claude"], "absent")


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------


class TestValidate(_SandboxBase):
    def test_passes_for_well_formed(self) -> None:
        rc, out = self.run_cli("validate")
        self.assertEqual(rc, 0)
        self.assertIn("ok   alpha-skill", out)

    def test_fails_for_missing_frontmatter(self) -> None:
        (self.repo / "alpha-skill" / "SKILL.md").write_text("# no frontmatter\n")
        rc, out = self.run_cli("validate")
        self.assertEqual(rc, 1)
        self.assertIn("FAIL alpha-skill", out)

    def test_fails_for_name_mismatch(self) -> None:
        (self.repo / "alpha-skill" / "SKILL.md").write_text(
            "---\nname: wrong-name\ndescription: x\n---\n"
        )
        rc, out = self.run_cli("validate")
        self.assertEqual(rc, 1)
        self.assertIn("name", out)


# ---------------------------------------------------------------------------
# Doctor
# ---------------------------------------------------------------------------


class TestDoctor(_SandboxBase):
    def test_clean_when_no_links(self) -> None:
        rc, out = self.run_cli("doctor")
        self.assertEqual(rc, 0)
        self.assertIn("clean", out)

    def test_detects_mismatched_symlink(self) -> None:
        (self.claude / "skills").mkdir(parents=True, exist_ok=True)
        (self.claude / "skills" / "alpha-skill").symlink_to(self.repo / "beta-skill")
        rc, out = self.run_cli("doctor")
        self.assertEqual(rc, 1)
        self.assertIn("alpha-skill", out)
        self.assertIn("mismatched-symlink", out)

    def test_detects_broken_symlink_to_repo(self) -> None:
        # symlink whose target name still lives in the repo namespace but
        # points into the repo at a path that no longer exists.
        (self.claude / "skills").mkdir(parents=True, exist_ok=True)
        (self.claude / "skills" / "alpha-skill").symlink_to(self.repo / "ghost")
        rc, out = self.run_cli("doctor")
        self.assertEqual(rc, 1)
        self.assertIn("broken-symlink", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
