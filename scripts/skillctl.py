#!/usr/bin/env python3
"""skillctl — deploy sincerity-skills to Hermes / Claude Code / Codex via symlink.

Single-file CLI, Python stdlib only. No third-party dependencies.

Source of truth:
    The directory containing this script's parent (auto-detected as the
    sincerity-skills repo root). Each immediate subdirectory containing a
    SKILL.md file is a "skill".

Targets:
    claude            -> ~/.claude/skills/<skill>
    codex             -> ~/.codex/skills/<skill>
    hermes:<profile>  -> ~/.hermes/profiles/<profile>/skills/<skill>
                         (or ~/.hermes/skills/<skill> when profile == "default")
    hermes:*          -> every detected Hermes profile (incl. "default")

Bare ``hermes`` is rejected on purpose — the caller must pick a profile so
they don't deploy into the wrong one. Use ``skillctl targets`` to list.

Design notes:
    - Deploy creates a symlink. Update happens by `git pull` on the source.
    - Never overwrites a real directory at the target. Errors loudly instead.
    - Replacing a symlink that points elsewhere requires --force.
    - All path roots are overridable via env vars so tests stay hermetic:
        SKILLCTL_CLAUDE_HOME  -> defaults to $HOME/.claude
        SKILLCTL_CODEX_HOME   -> defaults to $HOME/.codex
        SKILLCTL_HERMES_HOME  -> defaults to $HOME/.hermes
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


def repo_root() -> Path:
    """Return the sincerity-skills repo root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def claude_home() -> Path:
    return Path(os.environ.get("SKILLCTL_CLAUDE_HOME") or (Path.home() / ".claude"))


def codex_home() -> Path:
    return Path(os.environ.get("SKILLCTL_CODEX_HOME") or (Path.home() / ".codex"))


def hermes_home() -> Path:
    return Path(os.environ.get("SKILLCTL_HERMES_HOME") or (Path.home() / ".hermes"))


# ---------------------------------------------------------------------------
# Skill discovery + frontmatter
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Skill:
    name: str
    path: Path

    @property
    def skill_md(self) -> Path:
        return self.path / "SKILL.md"


def discover_skills(root: Optional[Path] = None) -> list[Skill]:
    root = root or repo_root()
    skills: list[Skill] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith(".") or child.name in {"scripts", "tests"}:
            continue
        if (child / "SKILL.md").is_file():
            skills.append(Skill(name=child.name, path=child))
    return skills


_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text: str) -> dict:
    """Parse top-of-file YAML-ish frontmatter into a dict.

    Supports the subset sincerity-skills uses:
      - simple key: value pairs
      - list values written as
            triggers:
              - foo
              - bar
      - scalar string values may be quoted or bare (no multi-line scalars)
    Anything more exotic is rejected with a clear error.
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError("missing YAML frontmatter (--- ... --- block at top of file)")
    body = m.group(1)
    out: dict = {}
    current_key: Optional[str] = None
    for raw in body.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - ") or line.startswith("\t- "):
            if current_key is None:
                raise ValueError(f"orphan list item: {raw!r}")
            value = line.split("- ", 1)[1].strip()
            out[current_key].append(_unquote(value))
            continue
        if line.startswith(("  ", "\t")):
            raise ValueError(f"unsupported indented line: {raw!r}")
        if ":" not in line:
            raise ValueError(f"unparsable line (no ':'): {raw!r}")
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if not val:
            out[key] = []
            current_key = key
        else:
            out[key] = _unquote(val)
            current_key = None
    return out


def _unquote(s: str) -> str:
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1]
    return s


# ---------------------------------------------------------------------------
# Targets
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Target:
    """Resolved deployment target. ``slug`` is what the user typed (e.g.
    ``hermes:deepkkumi``); ``skills_dir`` is where ``<skill>`` symlinks land."""

    slug: str
    skills_dir: Path


def hermes_profiles() -> list[str]:
    """Return ['default', <profile>, ...] sorted with default first.

    'default' represents ``~/.hermes/skills/`` (the no-profile root). Named
    profiles live under ``~/.hermes/profiles/<name>/``.
    """
    h = hermes_home()
    profiles = ["default"] if h.is_dir() else []
    pdir = h / "profiles"
    if pdir.is_dir():
        for child in sorted(pdir.iterdir()):
            if child.is_dir() and not child.name.startswith("."):
                profiles.append(child.name)
    return profiles


def resolve_target(slug: str) -> list[Target]:
    """Resolve a user-supplied target slug to one or more Targets.

    Raises SystemExit with a friendly message for bad input.
    """
    if slug == "claude":
        return [Target("claude", claude_home() / "skills")]
    if slug == "codex":
        return [Target("codex", codex_home() / "skills")]
    if slug == "hermes":
        avail = hermes_profiles()
        msg = (
            "Bare 'hermes' target is ambiguous — pick a profile.\n"
            f"Available: {', '.join('hermes:' + p for p in avail) or '(none)'}\n"
            "Or use 'hermes:*' for every detected profile."
        )
        raise SystemExit(msg)
    if slug.startswith("hermes:"):
        profile = slug[len("hermes:"):]
        if profile == "*":
            return [_hermes_target(p) for p in hermes_profiles()]
        if not profile:
            raise SystemExit("empty Hermes profile name")
        if profile != "default" and not _hermes_profile_dir(profile).is_dir():
            avail = hermes_profiles()
            raise SystemExit(
                f"Hermes profile '{profile}' not found.\n"
                f"Available: {', '.join(avail) or '(none)'}"
            )
        return [_hermes_target(profile)]
    raise SystemExit(f"unknown target: {slug!r}")


def _hermes_profile_dir(profile: str) -> Path:
    return hermes_home() / "profiles" / profile


def _hermes_target(profile: str) -> Target:
    if profile == "default":
        return Target("hermes:default", hermes_home() / "skills")
    return Target(f"hermes:{profile}", _hermes_profile_dir(profile) / "skills")


def all_known_targets() -> list[Target]:
    """All targets that actually exist on this machine."""
    out: list[Target] = []
    if claude_home().is_dir():
        out.append(Target("claude", claude_home() / "skills"))
    if codex_home().is_dir():
        out.append(Target("codex", codex_home() / "skills"))
    for p in hermes_profiles():
        out.append(_hermes_target(p))
    return out


# ---------------------------------------------------------------------------
# Symlink ops
# ---------------------------------------------------------------------------


def _link_state(link: Path, expected: Path) -> str:
    """Return one of:
       'absent', 'matches', 'mismatched-symlink',
       'real-directory', 'real-file', 'broken-symlink'
    """
    if link.is_symlink():
        try:
            actual = link.resolve(strict=False)
        except OSError:
            return "broken-symlink"
        if not actual.exists():
            return "broken-symlink"
        if actual == expected.resolve():
            return "matches"
        return "mismatched-symlink"
    if not link.exists():
        return "absent"
    if link.is_dir():
        return "real-directory"
    return "real-file"


def deploy_one(skill: Skill, target: Target, *, force: bool = False) -> str:
    """Deploy a single skill to a single target. Returns a status string."""
    target.skills_dir.mkdir(parents=True, exist_ok=True)
    link = target.skills_dir / skill.name
    state = _link_state(link, skill.path)
    if state == "matches":
        return "ok (already linked)"
    if state == "absent":
        link.symlink_to(skill.path)
        return "linked"
    if state == "broken-symlink":
        link.unlink()
        link.symlink_to(skill.path)
        return "linked (replaced broken symlink)"
    if state == "mismatched-symlink":
        if not force:
            return "skipped (different symlink exists; use --force)"
        link.unlink()
        link.symlink_to(skill.path)
        return "linked (replaced existing symlink)"
    if state == "real-directory":
        return "ERROR (real directory present — refusing to overwrite)"
    return "ERROR (file present where skill dir expected)"


def undeploy_one(skill_name: str, target: Target, *, force: bool = False) -> str:
    link = target.skills_dir / skill_name
    if not link.exists() and not link.is_symlink():
        return "absent"
    if link.is_symlink():
        link.unlink()
        return "removed"
    if link.is_dir() and force:
        # Only allow removing real directories with --force, and only if empty,
        # to keep the destructive surface tiny.
        try:
            link.rmdir()
            return "removed (empty real directory; --force)"
        except OSError:
            return "ERROR (real non-empty directory; aborting)"
    return "skipped (real directory; use --force to remove if empty)"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_list(args: argparse.Namespace) -> int:
    skills = discover_skills()
    if args.json:
        print(json.dumps([{"name": s.name, "path": str(s.path)} for s in skills], indent=2))
        return 0
    if not skills:
        print("(no skills found)")
        return 0
    print(f"{len(skills)} skill(s) in {repo_root()}")
    for s in skills:
        print(f"  {s.name}")
    return 0


def cmd_targets(args: argparse.Namespace) -> int:
    targets = all_known_targets()
    if args.json:
        print(json.dumps([{"slug": t.slug, "skills_dir": str(t.skills_dir)} for t in targets], indent=2))
        return 0
    if not targets:
        print("(no targets detected)")
        return 0
    print(f"{len(targets)} target(s) detected:")
    for t in targets:
        marker = "  " if t.skills_dir.exists() else "* "
        print(f"  {marker}{t.slug:<24} {t.skills_dir}")
    if any(not t.skills_dir.exists() for t in targets):
        print("  (* = skills/ dir does not yet exist; will be created on deploy)")
    return 0


def _resolve_skills(names: Iterable[str], *, all_skills: bool) -> list[Skill]:
    available = {s.name: s for s in discover_skills()}
    if all_skills:
        if list(names):
            raise SystemExit("--all is mutually exclusive with explicit skill names")
        return list(available.values())
    if not names:
        raise SystemExit("no skills specified (give names or pass --all)")
    out = []
    for n in names:
        if n not in available:
            raise SystemExit(
                f"unknown skill: {n!r}\n"
                f"Available: {', '.join(sorted(available)) or '(none)'}"
            )
        out.append(available[n])
    return out


def _resolve_targets(slugs: Iterable[str]) -> list[Target]:
    slugs = list(slugs)
    if not slugs:
        raise SystemExit(
            "at least one --target is required\n"
            "Examples: --target claude  --target hermes:default  --target hermes:*"
        )
    seen: dict[str, Target] = {}
    for slug in slugs:
        for t in resolve_target(slug):
            seen[t.slug] = t
    return list(seen.values())


def cmd_deploy(args: argparse.Namespace) -> int:
    skills = _resolve_skills(args.skills, all_skills=args.all)
    targets = _resolve_targets(args.target)
    rc = 0
    for t in targets:
        print(f"-> {t.slug}  ({t.skills_dir})")
        for s in skills:
            status = deploy_one(s, t, force=args.force)
            line = f"   {s.name:<40} {status}"
            print(line)
            if status.startswith("ERROR") or status.startswith("skipped"):
                rc = 1
    return rc


def cmd_undeploy(args: argparse.Namespace) -> int:
    targets = _resolve_targets(args.target)
    if not args.skills and not args.all:
        raise SystemExit("no skills specified (give names or pass --all)")
    if args.all:
        # For undeploy --all, undeploy every skill the source repo currently knows.
        names = [s.name for s in discover_skills()]
    else:
        names = list(args.skills)
    rc = 0
    for t in targets:
        print(f"-> {t.slug}  ({t.skills_dir})")
        for n in names:
            status = undeploy_one(n, t, force=args.force)
            line = f"   {n:<40} {status}"
            print(line)
            if status.startswith("ERROR"):
                rc = 1
    return rc


def cmd_status(args: argparse.Namespace) -> int:
    skills = discover_skills()
    targets = all_known_targets()
    if args.json:
        rows = []
        for s in skills:
            row = {"skill": s.name, "targets": {}}
            for t in targets:
                row["targets"][t.slug] = _link_state(t.skills_dir / s.name, s.path)
            rows.append(row)
        print(json.dumps(rows, indent=2))
        return 0
    if not skills:
        print("(no skills found)")
        return 0
    if not targets:
        print("(no targets detected)")
        return 0
    # Matrix print
    name_w = max(len(s.name) for s in skills)
    header = f"{'skill'.ljust(name_w)}  " + "  ".join(t.slug for t in targets)
    print(header)
    print("-" * len(header))
    for s in skills:
        cells = []
        for t in targets:
            state = _link_state(t.skills_dir / s.name, s.path)
            cells.append(_pretty_state(state).ljust(len(t.slug)))
        print(f"{s.name.ljust(name_w)}  " + "  ".join(cells))
    return 0


_STATE_GLYPH = {
    "matches": "OK",
    "absent": "-",
    "mismatched-symlink": "≠",
    "broken-symlink": "?",
    "real-directory": "DIR",
    "real-file": "FILE",
}


def _pretty_state(state: str) -> str:
    return _STATE_GLYPH.get(state, state)


def cmd_validate(args: argparse.Namespace) -> int:
    skills = discover_skills()
    rc = 0
    required = {"name", "description"}
    for s in skills:
        try:
            text = s.skill_md.read_text(encoding="utf-8")
        except OSError as e:
            print(f"FAIL {s.name}: cannot read SKILL.md ({e})")
            rc = 1
            continue
        try:
            fm = parse_frontmatter(text)
        except ValueError as e:
            print(f"FAIL {s.name}: {e}")
            rc = 1
            continue
        missing = required - fm.keys()
        problems = []
        if missing:
            problems.append(f"missing keys: {sorted(missing)}")
        if "name" in fm and fm["name"] != s.name:
            problems.append(f"name {fm['name']!r} != directory {s.name!r}")
        if problems:
            print(f"FAIL {s.name}: " + "; ".join(problems))
            rc = 1
        else:
            print(f"ok   {s.name}")
    return rc


def cmd_doctor(args: argparse.Namespace) -> int:
    """Detect broken/mismatched symlinks across all detected targets."""
    skills = {s.name: s for s in discover_skills()}
    targets = all_known_targets()
    issues = 0
    for t in targets:
        if not t.skills_dir.exists():
            continue
        for entry in sorted(t.skills_dir.iterdir()):
            # Only inspect entries whose name matches one of *our* skills, OR
            # entries that are symlinks pointing into our repo (in case the
            # source skill was deleted).
            try:
                resolves_into_repo = (
                    entry.is_symlink()
                    and str(entry.resolve(strict=False)).startswith(str(repo_root()))
                )
            except OSError:
                resolves_into_repo = False
            if entry.name not in skills and not resolves_into_repo:
                continue
            expected = (skills.get(entry.name).path
                        if entry.name in skills else Path("/nonexistent"))
            state = _link_state(entry, expected)
            if state in ("matches", "absent"):
                continue
            print(f"{t.slug}/{entry.name}: {state}")
            issues += 1
    if issues == 0:
        print("doctor: clean")
    return 1 if issues else 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="skillctl",
        description="Deploy sincerity-skills to Claude / Codex / Hermes via symlink.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("list", help="list discovered skills in this repo")
    pl.add_argument("--json", action="store_true")
    pl.set_defaults(func=cmd_list)

    pt = sub.add_parser("targets", help="list deployment targets detected on this machine")
    pt.add_argument("--json", action="store_true")
    pt.set_defaults(func=cmd_targets)

    pd = sub.add_parser("deploy", help="symlink one or more skills into target(s)")
    pd.add_argument("skills", nargs="*")
    pd.add_argument("--all", action="store_true", help="deploy every skill in the repo")
    pd.add_argument("--target", "-t", action="append", default=[],
                    help="target slug (claude | codex | hermes:<profile> | hermes:*); repeatable")
    pd.add_argument("--force", action="store_true",
                    help="replace mismatched symlinks (never replaces real directories)")
    pd.set_defaults(func=cmd_deploy)

    pu = sub.add_parser("undeploy", help="remove skill symlinks from target(s)")
    pu.add_argument("skills", nargs="*")
    pu.add_argument("--all", action="store_true")
    pu.add_argument("--target", "-t", action="append", default=[])
    pu.add_argument("--force", action="store_true",
                    help="also remove a target entry if it is an empty real directory")
    pu.set_defaults(func=cmd_undeploy)

    ps = sub.add_parser("status", help="show deploy state matrix (skill x target)")
    ps.add_argument("--json", action="store_true")
    ps.set_defaults(func=cmd_status)

    pv = sub.add_parser("validate", help="validate every skill's SKILL.md frontmatter")
    pv.set_defaults(func=cmd_validate)

    pdoc = sub.add_parser("doctor", help="diagnose broken/mismatched symlinks at known targets")
    pdoc.set_defaults(func=cmd_doctor)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
