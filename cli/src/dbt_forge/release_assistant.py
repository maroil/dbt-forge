"""Release preparation and publish helpers for dbt-forge."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CLI_ROOT = REPO_ROOT / "cli"
WEBSITE_ROOT = REPO_ROOT / "website"
VERSION_FILE = CLI_ROOT / "src" / "dbt_forge" / "__init__.py"
CHANGELOG_FILE = REPO_ROOT / "CHANGELOG.md"
README_FILE = REPO_ROOT / "README.md"
CLI_README_FILE = CLI_ROOT / "README.md"
RELEASING_FILE = REPO_ROOT / "RELEASING.md"
CONTRIBUTING_FILE = REPO_ROOT / "CONTRIBUTING.md"
WEBSITE_DEVELOPMENT_FILE = WEBSITE_ROOT / "src" / "content" / "docs" / "docs" / "development.md"
WEBSITE_GETTING_STARTED_FILE = (
    WEBSITE_ROOT / "src" / "content" / "docs" / "docs" / "getting-started.md"
)
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
UNRELEASED_STUB = "### Added\n\n- Nothing yet."
RELEASE_NOTES_INTRO = (
    "This project is preparing the Python CLI package release `dbt-forge` version `{version}`."
)


@dataclass(slots=True)
class CheckResult:
    """Outcome of a release verification check."""

    status: str
    name: str
    detail: str


class ReleaseAssistantError(RuntimeError):
    """Raised when a release step cannot continue safely."""


def parse_version(version: str) -> str:
    """Validate and normalize a semantic version string."""
    version = version.strip()
    if not VERSION_RE.fullmatch(version):
        raise ReleaseAssistantError(
            f"Invalid version '{version}'. Expected semantic version like 0.2.0."
        )
    return version


def run_command(
    args: list[str],
    *,
    cwd: Path,
    check: bool = True,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Execute a subprocess and return the completed process."""
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=capture_output,
        check=check,
    )


def read_text(path: Path) -> str:
    """Read UTF-8 text from disk."""
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    """Write UTF-8 text to disk."""
    path.write_text(content, encoding="utf-8")


def _replace_once(text: str, pattern: str, repl: str, *, file_label: str) -> str:
    updated, count = re.subn(pattern, repl, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise ReleaseAssistantError(f"Could not update {file_label}: pattern not found.")
    return updated


def update_version_file(content: str, version: str) -> str:
    """Set the package version constant."""
    return _replace_once(
        content,
        r'^__version__ = "[^"]+"$',
        f'__version__ = "{version}"',
        file_label="cli/src/dbt_forge/__init__.py",
    )


def update_root_readme(content: str, version: str) -> str:
    """Refresh release assistant examples in the repository README when present."""
    if "python3 scripts/release_assistant.py prepare" not in content:
        return content
    return update_release_command_examples(content, version, file_label="README.md")


def update_cli_readme(content: str, version: str) -> str:
    """Update the major/minor alpha phase in the CLI README."""
    content = _replace_once(
        content,
        r"The project is currently in its `\d+\.\d+\.x` alpha phase\.",
        f"The project is currently in its `{version.rsplit('.', 1)[0]}.x` alpha phase.",
        file_label="cli/README.md",
    )
    return update_release_command_examples(content, version, file_label="cli/README.md")


def update_website_getting_started(content: str, version: str) -> str:
    """Update the website quickstart alpha track to match the release series."""
    return _replace_once(
        content,
        r"This guide covers the current `\d+\.\d+\.x` alpha\.",
        f"This guide covers the current `{version.rsplit('.', 1)[0]}.x` alpha.",
        file_label="website/src/content/docs/docs/getting-started.md",
    )


def update_release_command_examples(content: str, version: str, *, file_label: str) -> str:
    """Refresh embedded release assistant examples in docs."""
    cmd = "python3 scripts/release_assistant.py"
    ver_re = r"[0-9]+\.[0-9]+\.[0-9]+"
    patterns = {
        rf"^{cmd} prepare {ver_re}$": f"{cmd} prepare {version}",
        rf"^{cmd} verify {ver_re}$": f"{cmd} verify {version}",
        rf"^{cmd} publish {ver_re} --confirm$": f"{cmd} publish {version} --confirm",
    }
    updated = content
    for pattern, repl in patterns.items():
        updated, count = re.subn(pattern, repl, updated, count=1, flags=re.MULTILINE)
        if count != 1:
            raise ReleaseAssistantError(
                f"Could not update {file_label}: release command not found."
            )
    return updated


def update_releasing_doc(content: str, version: str, release_date: str) -> str:
    """Refresh the pinned release version in the release guide."""
    content = _replace_once(
        content,
        r"This project is preparing the Python CLI package release `dbt-forge` version `[^`]+`\.",
        RELEASE_NOTES_INTRO.format(version=version),
        file_label="RELEASING.md",
    )
    content = _replace_once(
        content,
        r"^Verified on \d{4}-\d{2}-\d{2} from the local environment:$",
        f"Verified on {release_date} from the local environment:",
        file_label="RELEASING.md",
    )
    content = _replace_once(
        content,
        r"^- Current package version in source: `[^`]+`$",
        f"- Current package version in source: `{version}`",
        file_label="RELEASING.md",
    )
    content = update_release_command_examples(content, version, file_label="RELEASING.md")
    content = _replace_once(
        content,
        r"^5\. Let the script create and push tag `v[^`]+`\.$",
        f"5. Let the script create and push tag `v{version}`.",
        file_label="RELEASING.md",
    )
    inline_patterns = {
        (
            r"Run `python3 scripts/release_assistant.py verify "
            r"[0-9]+\.[0-9]+\.[0-9]+` on"
        ): f"Run `python3 scripts/release_assistant.py verify {version}` on",
        (
            r"^3\. Run `python3 scripts/release_assistant.py verify "
            r"[0-9]+\.[0-9]+\.[0-9]+`\.$"
        ): f"3. Run `python3 scripts/release_assistant.py verify {version}`.",
        (
            r"^4\. Run `python3 scripts/release_assistant.py publish "
            r"[0-9]+\.[0-9]+\.[0-9]+ --confirm`\.$"
        ): f"4. Run `python3 scripts/release_assistant.py publish {version} --confirm`.",
    }
    for pattern, repl in inline_patterns.items():
        content = _replace_once(content, pattern, repl, file_label="RELEASING.md")
    content = _replace_once(
        content,
        r"^7\. Create the GitHub Release using the `[^`]+` changelog entry\.$",
        f"7. Create the GitHub Release using the `{version}` changelog entry.",
        file_label="RELEASING.md",
    )
    return content


def _extract_section_body(content: str, header_pattern: str) -> tuple[int, int, str] | None:
    match = re.search(header_pattern, content, flags=re.MULTILINE)
    if not match:
        return None
    start = match.end()
    next_header = re.search(r"^## \[", content[start:], flags=re.MULTILINE)
    end = start + next_header.start() if next_header else len(content)
    return match.start(), end, content[start:end]


def _has_changelog_entries(body: str) -> bool:
    return any(line.lstrip().startswith("- ") for line in body.splitlines())


def promote_unreleased_section(content: str, version: str, release_date: str) -> str:
    """Move the unreleased changelog body into the target version section."""
    released = get_changelog_section(content, version)
    if released is not None:
        return content

    section = _extract_section_body(content, r"^## \[Unreleased\]\n")
    if section is None:
        raise ReleaseAssistantError("CHANGELOG.md is missing the [Unreleased] section.")

    start, end, body = section
    cleaned_body = body.strip()
    if not _has_changelog_entries(cleaned_body):
        raise ReleaseAssistantError(
            "CHANGELOG.md has no unreleased entries to promote for this release."
        )

    replacement = (
        "## [Unreleased]\n\n"
        f"{UNRELEASED_STUB}\n\n"
        f"## [{version}] - {release_date}\n\n"
        f"{cleaned_body}\n\n"
    )
    remainder = content[end:].lstrip("\n")
    prefix = content[:start]
    return prefix + replacement + remainder


def get_changelog_section(content: str, version: str) -> str | None:
    """Return the markdown body for a released changelog section."""
    pattern = rf"^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}\n"
    section = _extract_section_body(content, pattern)
    if section is None:
        return None
    return section[2].strip()


def extract_version_from_version_file(content: str) -> str:
    match = re.search(r'^__version__ = "([^"]+)"$', content, flags=re.MULTILINE)
    if not match:
        raise ReleaseAssistantError("Could not parse version from cli/src/dbt_forge/__init__.py.")
    return match.group(1)


def extract_releasing_target(content: str) -> str:
    match = re.search(
        r"This project is preparing the Python CLI package release `dbt-forge` version `([^`]+)`\.",
        content,
    )
    if not match:
        raise ReleaseAssistantError("Could not parse release target from RELEASING.md.")
    return match.group(1)


def extract_website_getting_started_track(content: str) -> str:
    match = re.search(
        r"This guide covers the current `(\d+\.\d+)\.x` alpha\.",
        content,
    )
    if not match:
        raise ReleaseAssistantError(
            "Could not parse alpha track from website/src/content/docs/docs/getting-started.md."
        )
    return match.group(1)


def prepare_release(
    version: str,
    *,
    repo_root: Path = REPO_ROOT,
    today: date | None = None,
) -> list[Path]:
    """Update versioned release metadata for the target release."""
    version = parse_version(version)
    release_date = (today or date.today()).isoformat()
    changed: list[Path] = []
    updates = {
        VERSION_FILE.relative_to(REPO_ROOT): lambda text: update_version_file(text, version),
        README_FILE.relative_to(REPO_ROOT): lambda text: update_root_readme(text, version),
        CLI_README_FILE.relative_to(REPO_ROOT): lambda text: update_cli_readme(text, version),
        CONTRIBUTING_FILE.relative_to(REPO_ROOT): lambda text: update_release_command_examples(
            text, version, file_label="CONTRIBUTING.md"
        ),
        RELEASING_FILE.relative_to(REPO_ROOT): lambda text: update_releasing_doc(
            text, version, release_date
        ),
        WEBSITE_DEVELOPMENT_FILE.relative_to(REPO_ROOT): (
            lambda text: update_release_command_examples(
                text, version, file_label="website/src/content/docs/docs/development.md"
            )
        ),
        WEBSITE_GETTING_STARTED_FILE.relative_to(REPO_ROOT): (
            lambda text: update_website_getting_started(text, version)
        ),
        CHANGELOG_FILE.relative_to(REPO_ROOT): lambda text: promote_unreleased_section(
            text, version, release_date
        ),
    }
    for relative_path, updater in updates.items():
        path = repo_root / relative_path
        original = read_text(path)
        updated = updater(original)
        if updated != original:
            write_text(path, updated)
            changed.append(path)
    return changed


def _git_output(
    args: list[str],
    *,
    repo_root: Path,
    runner=run_command,
) -> str:
    result = runner(args, cwd=repo_root)
    return result.stdout.strip()


def _command_summary(output: str) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return "completed successfully"
    return lines[-1]


def _warn_lines(output: str) -> list[str]:
    return [
        line.strip() for line in output.splitlines() if "[WARN]" in line or line.startswith("WARN")
    ]


def verify_release(
    version: str,
    *,
    repo_root: Path = REPO_ROOT,
    runner=run_command,
) -> list[CheckResult]:
    """Run release-readiness checks and return a summarized report."""
    version = parse_version(version)
    results: list[CheckResult] = []

    status_output = _git_output(
        ["git", "status", "--porcelain"], repo_root=repo_root, runner=runner
    )
    if status_output:
        results.append(CheckResult("FAIL", "git worktree", "worktree has uncommitted changes"))
        return results
    results.append(CheckResult("PASS", "git worktree", "worktree is clean"))

    branch = _git_output(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], repo_root=repo_root, runner=runner
    )
    if branch != "main":
        results.append(CheckResult("FAIL", "git branch", f"expected main, found {branch}"))
        return results
    results.append(CheckResult("PASS", "git branch", "on main"))

    runner(["git", "fetch", "origin", "main"], cwd=repo_root)
    local_main = _git_output(["git", "rev-parse", "HEAD"], repo_root=repo_root, runner=runner)
    remote_main = _git_output(
        ["git", "rev-parse", "origin/main"], repo_root=repo_root, runner=runner
    )
    if local_main != remote_main:
        results.append(CheckResult("FAIL", "git sync", "main is not aligned with origin/main"))
        return results
    results.append(CheckResult("PASS", "git sync", "main matches origin/main"))

    version_checks = {
        "package version": (
            extract_version_from_version_file(
                read_text(repo_root / VERSION_FILE.relative_to(REPO_ROOT))
            ),
            version,
        ),
        "RELEASING target": (
            extract_releasing_target(read_text(repo_root / RELEASING_FILE.relative_to(REPO_ROOT))),
            version,
        ),
        "website quickstart track": (
            extract_website_getting_started_track(
                read_text(repo_root / WEBSITE_GETTING_STARTED_FILE.relative_to(REPO_ROOT))
            ),
            version.rsplit(".", 1)[0],
        ),
    }
    mismatches = [
        f"{name}={actual}"
        for name, (actual, expected) in version_checks.items()
        if actual != expected
    ]
    changelog_text = read_text(repo_root / CHANGELOG_FILE.relative_to(REPO_ROOT))
    if get_changelog_section(changelog_text, version) is None:
        mismatches.append("CHANGELOG.md missing released section")
    if mismatches:
        results.append(CheckResult("FAIL", "version consistency", "; ".join(mismatches)))
        return results
    results.append(
        CheckResult("PASS", "version consistency", f"all release metadata points to {version}")
    )

    cli_commands = [
        (["uv", "run", "ruff", "check", "."], CLI_ROOT, "cli lint"),
        (["uv", "run", "pytest"], CLI_ROOT, "cli tests"),
    ]
    for args, cwd, name in cli_commands:
        completed = runner(args, cwd=repo_root / cwd.relative_to(REPO_ROOT))
        results.append(CheckResult("PASS", name, _command_summary(completed.stdout)))

    with tempfile.TemporaryDirectory(prefix="dbt-forge-release-") as tmpdir:
        dist_dir = Path(tmpdir) / "dist"
        build_result = runner(
            ["uv", "build", "--clear", "--no-create-gitignore", "--out-dir", str(dist_dir)],
            cwd=repo_root / CLI_ROOT.relative_to(REPO_ROOT),
        )
        results.append(CheckResult("PASS", "cli build", _command_summary(build_result.stdout)))

        artifacts = sorted(
            str(path)
            for path in dist_dir.iterdir()
            if path.is_file() and (path.suffix == ".whl" or path.name.endswith(".tar.gz"))
        )
        if not artifacts:
            raise ReleaseAssistantError(
                "No artifacts were built into the temporary dist directory."
            )
        twine_result = runner(
            ["uvx", "twine", "check", *artifacts],
            cwd=repo_root / CLI_ROOT.relative_to(REPO_ROOT),
        )
        results.append(CheckResult("PASS", "twine check", _command_summary(twine_result.stdout)))

        wheel = dist_dir / f"dbt_forge-{version}-py3-none-any.whl"
        if not wheel.exists():
            raise ReleaseAssistantError(f"Expected built wheel {wheel.name} was not created.")
        _smoke_install_wheel(wheel)
        results.append(CheckResult("PASS", "wheel smoke install", wheel.name))

    website_build = runner(["pnpm", "build"], cwd=repo_root / WEBSITE_ROOT.relative_to(REPO_ROOT))
    warnings = _warn_lines(website_build.stdout)
    if warnings:
        results.append(
            CheckResult("WARN", "website build", f"{len(warnings)} warning(s): {warnings[0]}")
        )
    else:
        results.append(CheckResult("PASS", "website build", _command_summary(website_build.stdout)))

    return results


def _smoke_install_wheel(wheel_path: Path) -> None:
    python_bin = shutil.which("python3.12") or sys.executable
    with tempfile.TemporaryDirectory(prefix="dbt-forge-wheel-") as tmpdir:
        tmp_path = Path(tmpdir)
        venv_dir = tmp_path / "venv"
        subprocess.run([python_bin, "-m", "venv", str(venv_dir)], check=True, text=True)
        bindir = "Scripts" if sys.platform == "win32" else "bin"
        venv_python = venv_dir / bindir / ("python.exe" if sys.platform == "win32" else "python")
        venv_cli = venv_dir / bindir / ("dbt-forge.exe" if sys.platform == "win32" else "dbt-forge")
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"],
            check=True,
            text=True,
            capture_output=True,
        )
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", str(wheel_path)],
            check=True,
            text=True,
            capture_output=True,
        )
        subprocess.run([str(venv_cli), "--version"], check=True, text=True, capture_output=True)
        subprocess.run([str(venv_cli), "--help"], check=True, text=True, capture_output=True)


def ensure_release_ready(results: list[CheckResult]) -> None:
    """Raise if any verification result failed."""
    failures = [result for result in results if result.status == "FAIL"]
    if failures:
        joined = "; ".join(f"{result.name}: {result.detail}" for result in failures)
        raise ReleaseAssistantError(f"Release verification failed: {joined}")


def _latest_dispatch_run_id(repo_root: Path) -> str:
    """Locate the latest manually dispatched Release workflow run id."""
    deadline = time.time() + 30
    while time.time() < deadline:
        result = run_command(
            [
                "gh",
                "run",
                "list",
                "--workflow",
                "Release",
                "--branch",
                "main",
                "--event",
                "workflow_dispatch",
                "--limit",
                "1",
                "--json",
                "databaseId",
            ],
            cwd=repo_root,
        )
        runs = json.loads(result.stdout)
        if runs:
            run_id = runs[0].get("databaseId")
            if run_id:
                return str(run_id)
        time.sleep(2)
    raise ReleaseAssistantError("Could not find the manually dispatched Release workflow run.")


def publish_release(version: str, *, repo_root: Path = REPO_ROOT, confirm: bool = False) -> None:
    """Run the publish flow after verification succeeds."""
    version = parse_version(version)
    if not confirm:
        raise ReleaseAssistantError("Refusing to publish without --confirm.")

    results = verify_release(version, repo_root=repo_root)
    print_summary(results)
    ensure_release_ready(results)

    run_command(["gh", "workflow", "run", "Release", "--ref", "main"], cwd=repo_root)
    workflow_run_id = _latest_dispatch_run_id(repo_root)
    run_command(["gh", "run", "watch", workflow_run_id, "--exit-status"], cwd=repo_root)

    answer = input(
        "TestPyPI workflow completed. Verify the TestPyPI artifact, then type 'yes' to continue: "
    ).strip()
    if answer.lower() != "yes":
        raise ReleaseAssistantError("Publish stopped before tag creation.")

    existing_tag = run_command(
        ["git", "tag", "--list", f"v{version}"], cwd=repo_root
    ).stdout.strip()
    if existing_tag:
        raise ReleaseAssistantError(f"Tag v{version} already exists.")

    run_command(["git", "tag", f"v{version}"], cwd=repo_root)
    run_command(["git", "push", "origin", f"v{version}"], cwd=repo_root)

    changelog = read_text(repo_root / CHANGELOG_FILE.relative_to(REPO_ROOT))
    notes = get_changelog_section(changelog, version)
    if notes is None:
        raise ReleaseAssistantError(f"Could not find changelog notes for {version}.")

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as handle:
        notes_path = Path(handle.name)
        handle.write(notes)
    try:
        run_command(
            [
                "gh",
                "release",
                "create",
                f"v{version}",
                "--title",
                f"v{version}",
                "--notes-file",
                str(notes_path),
            ],
            cwd=repo_root,
        )
    finally:
        notes_path.unlink(missing_ok=True)


def print_summary(results: list[CheckResult]) -> None:
    """Print a compact PASS/WARN/FAIL summary."""
    for result in results:
        print(f"{result.status:<4} {result.name}: {result.detail}")
    overall = "RELEASE READY" if all(result.status != "FAIL" for result in results) else "NOT READY"
    print(f"\n{overall}")


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(description="Prepare, verify, and publish dbt-forge releases.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="Update release metadata for a version.")
    prepare.add_argument("version")

    verify = subparsers.add_parser("verify", help="Run release readiness checks.")
    verify.add_argument("version")

    publish = subparsers.add_parser("publish", help="Run the publish workflow for a version.")
    publish.add_argument("version")
    publish.add_argument("--confirm", action="store_true", help="Required to run publish steps.")

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            changed = prepare_release(args.version)
            if changed:
                print("Updated release files:")
                for path in changed:
                    print(f"- {path.relative_to(REPO_ROOT)}")
            else:
                print(f"Release metadata is already prepared for {parse_version(args.version)}.")
            return 0

        if args.command == "verify":
            results = verify_release(args.version)
            print_summary(results)
            ensure_release_ready(results)
            return 0

        if args.command == "publish":
            publish_release(args.version, confirm=args.confirm)
            print(f"Release publish flow started for v{parse_version(args.version)}.")
            return 0
    except ReleaseAssistantError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else ""
        stdout = exc.stdout.strip() if exc.stdout else ""
        detail = stderr or stdout or str(exc)
        print(f"ERROR: command failed: {detail}", file=sys.stderr)
        return exc.returncode or 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
