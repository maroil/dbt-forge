"""Tests for the release assistant workflow."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from dbt_forge import release_assistant


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _repo_fixture(tmp_path: Path) -> Path:
    _write(
        tmp_path / "cli" / "src" / "dbt_forge" / "__init__.py",
        '"""pkg"""\n\n__version__ = "0.1.1"\n',
    )
    _write(
        tmp_path / "README.md",
        "\n".join(
            [
                "# dbt-forge",
                "",
                "```bash",
                "python3 scripts/release_assistant.py prepare 0.1.1",
                "python3 scripts/release_assistant.py verify 0.1.1",
                "python3 scripts/release_assistant.py publish 0.1.1 --confirm",
                "```",
                "",
            ]
        ),
    )
    _write(
        tmp_path / "cli" / "README.md",
        "\n".join(
            [
                "The project is currently in its `0.1.x` alpha phase.",
                "",
                "```bash",
                "python3 scripts/release_assistant.py prepare 0.1.1",
                "python3 scripts/release_assistant.py verify 0.1.1",
                "python3 scripts/release_assistant.py publish 0.1.1 --confirm",
                "```",
                "",
            ]
        ),
    )
    _write(
        tmp_path / "CHANGELOG.md",
        (
            "# Changelog\n\n## [Unreleased]\n\n### Added\n\n- Added release automation.\n\n"
            "## [0.1.1] - 2026-03-08\n\n- Previous release.\n"
        ),
    )
    _write(
        tmp_path / "RELEASING.md",
        "\n".join(
            [
                "# Releasing `dbt-forge`",
                "",
                (
                    "This project is preparing the Python CLI package release "
                    "`dbt-forge` version `0.1.1`."
                ),
                "",
                "Verified on 2026-03-08 from the local environment:",
                "- Current package version in source: `0.1.1`",
                "",
                "```bash",
                "python3 scripts/release_assistant.py prepare 0.1.1",
                "python3 scripts/release_assistant.py verify 0.1.1",
                "python3 scripts/release_assistant.py publish 0.1.1 --confirm",
                "```",
                "",
                "Run `python3 scripts/release_assistant.py verify 0.1.1` on the exact commit.",
                "3. Run `python3 scripts/release_assistant.py verify 0.1.1`.",
                "4. Run `python3 scripts/release_assistant.py publish 0.1.1 --confirm`.",
                "5. Let the script create and push tag `v0.1.1`.",
                "7. Create the GitHub Release using the `0.1.1` changelog entry.",
                "",
            ]
        ),
    )
    _write(
        tmp_path / "CONTRIBUTING.md",
        "\n".join(
            [
                "```bash",
                "python3 scripts/release_assistant.py prepare 0.1.1",
                "python3 scripts/release_assistant.py verify 0.1.1",
                "python3 scripts/release_assistant.py publish 0.1.1 --confirm",
                "```",
                "",
            ]
        ),
    )
    _write(
        tmp_path / "website" / "src" / "content" / "docs" / "docs" / "development.md",
        "\n".join(
            [
                "```bash",
                "python3 scripts/release_assistant.py prepare 0.1.1",
                "python3 scripts/release_assistant.py verify 0.1.1",
                "python3 scripts/release_assistant.py publish 0.1.1 --confirm",
                "```",
                "",
            ]
        ),
    )
    _write(
        tmp_path / "website" / "src" / "content" / "docs" / "docs" / "getting-started.md",
        "\n".join(
            [
                "This guide covers the current `0.1.x` alpha.",
                "",
            ]
        ),
    )
    return tmp_path


def test_parse_version_rejects_invalid_values() -> None:
    with pytest.raises(release_assistant.ReleaseAssistantError):
        release_assistant.parse_version("0.2")


def test_promote_unreleased_section_creates_release_and_stub() -> None:
    content = (
        "# Changelog\n\n## [Unreleased]\n\n### Added\n\n- Added release automation.\n\n"
        "## [0.1.1] - 2026-03-08\n\n- Previous release.\n"
    )

    updated = release_assistant.promote_unreleased_section(content, "0.2.0", "2026-03-09")

    assert "## [0.2.0] - 2026-03-09" in updated
    assert "## [Unreleased]\n\n### Added\n\n- Nothing yet." in updated
    assert "- Added release automation." in updated


def test_get_changelog_section_returns_release_notes() -> None:
    content = (
        "# Changelog\n\n## [Unreleased]\n\n### Added\n\n- Nothing yet.\n\n"
        "## [0.2.0] - 2026-03-09\n\n### Added\n\n- Added release automation.\n"
    )

    notes = release_assistant.get_changelog_section(content, "0.2.0")

    assert notes == "### Added\n\n- Added release automation."


def test_update_root_readme_is_noop_without_release_commands() -> None:
    content = "# dbt-forge\n\nNo release commands here.\n"

    updated = release_assistant.update_root_readme(content, "0.2.0")

    assert updated == content


def test_update_website_getting_started_updates_alpha_track() -> None:
    content = "This guide covers the current `0.1.x` alpha.\n"

    updated = release_assistant.update_website_getting_started(content, "0.2.3")

    assert "This guide covers the current `0.2.x` alpha." in updated


def test_prepare_release_updates_all_release_files(tmp_path: Path) -> None:
    repo_root = _repo_fixture(tmp_path)

    changed = release_assistant.prepare_release(
        "0.2.0", repo_root=repo_root, today=date(2026, 3, 9)
    )

    assert repo_root / "README.md" in changed
    assert "0.2.0" in (repo_root / "cli" / "src" / "dbt_forge" / "__init__.py").read_text()
    assert "## [0.2.0] - 2026-03-09" in (repo_root / "CHANGELOG.md").read_text()
    assert (
        "python3 scripts/release_assistant.py publish 0.2.0 --confirm"
        in (repo_root / "RELEASING.md").read_text()
    )
    assert (
        "This guide covers the current `0.2.x` alpha."
        in (
            repo_root / "website" / "src" / "content" / "docs" / "docs" / "getting-started.md"
        ).read_text()
    )


def test_verify_release_fails_on_dirty_worktree(tmp_path: Path) -> None:
    repo_root = _repo_fixture(tmp_path)

    def fake_runner(args: list[str], *, cwd: Path, check: bool = True, capture_output: bool = True):
        assert cwd == repo_root
        if args == ["git", "status", "--porcelain"]:
            return CompletedProcess(args, 0, " M README.md\n", "")
        raise AssertionError(f"Unexpected command: {args}")

    results = release_assistant.verify_release("0.1.1", repo_root=repo_root, runner=fake_runner)

    assert results == [
        release_assistant.CheckResult("FAIL", "git worktree", "worktree has uncommitted changes")
    ]


def test_verify_release_fails_on_branch_mismatch(tmp_path: Path) -> None:
    repo_root = _repo_fixture(tmp_path)

    def fake_runner(args: list[str], *, cwd: Path, check: bool = True, capture_output: bool = True):
        assert cwd == repo_root
        if args == ["git", "status", "--porcelain"]:
            return CompletedProcess(args, 0, "", "")
        if args == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
            return CompletedProcess(args, 0, "release/0.2.0\n", "")
        raise AssertionError(f"Unexpected command: {args}")

    results = release_assistant.verify_release("0.1.1", repo_root=repo_root, runner=fake_runner)

    assert results[-1] == release_assistant.CheckResult(
        "FAIL", "git branch", "expected main, found release/0.2.0"
    )


def test_verify_release_fails_on_missing_release_section(tmp_path: Path) -> None:
    repo_root = _repo_fixture(tmp_path)
    (repo_root / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [Unreleased]\n\n### Added\n\n- Added release automation.\n",
        encoding="utf-8",
    )

    def fake_runner(args: list[str], *, cwd: Path, check: bool = True, capture_output: bool = True):
        if cwd == repo_root and args == ["git", "status", "--porcelain"]:
            return CompletedProcess(args, 0, "", "")
        if cwd == repo_root and args == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
            return CompletedProcess(args, 0, "main\n", "")
        if cwd == repo_root and args == ["git", "fetch", "origin", "main"]:
            return CompletedProcess(args, 0, "", "")
        if cwd == repo_root and args == ["git", "rev-parse", "HEAD"]:
            return CompletedProcess(args, 0, "abc\n", "")
        if cwd == repo_root and args == ["git", "rev-parse", "origin/main"]:
            return CompletedProcess(args, 0, "abc\n", "")
        raise AssertionError(f"Unexpected command: {args}")

    results = release_assistant.verify_release("0.1.1", repo_root=repo_root, runner=fake_runner)

    assert results[-1].status == "FAIL"
    assert "CHANGELOG.md missing released section" in results[-1].detail


def test_verify_release_uses_temp_dist_and_target_wheel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _repo_fixture(tmp_path)
    release_assistant.prepare_release("0.2.0", repo_root=repo_root, today=date(2026, 3, 9))
    _write(
        repo_root / "cli" / "dist" / "dbt_forge-0.1.1-py3-none-any.whl",
        "stale wheel",
    )

    smoke_installs: list[Path] = []

    def fake_smoke_install(path: Path) -> None:
        smoke_installs.append(path)

    monkeypatch.setattr(release_assistant, "_smoke_install_wheel", fake_smoke_install)

    def fake_runner(args: list[str], *, cwd: Path, check: bool = True, capture_output: bool = True):
        if cwd == repo_root and args == ["git", "status", "--porcelain"]:
            return CompletedProcess(args, 0, "", "")
        if cwd == repo_root and args == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
            return CompletedProcess(args, 0, "main\n", "")
        if cwd == repo_root and args == ["git", "fetch", "origin", "main"]:
            return CompletedProcess(args, 0, "", "")
        if cwd == repo_root and args == ["git", "rev-parse", "HEAD"]:
            return CompletedProcess(args, 0, "abc\n", "")
        if cwd == repo_root and args == ["git", "rev-parse", "origin/main"]:
            return CompletedProcess(args, 0, "abc\n", "")
        if cwd == repo_root / "cli" and args == ["uv", "run", "ruff", "check", "."]:
            return CompletedProcess(args, 0, "All checks passed!\n", "")
        if cwd == repo_root / "cli" and args == ["uv", "run", "pytest"]:
            return CompletedProcess(args, 0, "113 passed in 2.27s\n", "")
        if cwd == repo_root / "cli" and args[:5] == [
            "uv",
            "build",
            "--clear",
            "--no-create-gitignore",
            "--out-dir",
        ]:
            dist_dir = Path(args[5])
            dist_dir.mkdir(parents=True, exist_ok=True)
            (dist_dir / "dbt_forge-0.2.0-py3-none-any.whl").write_text("wheel", encoding="utf-8")
            (dist_dir / "dbt_forge-0.2.0.tar.gz").write_text("sdist", encoding="utf-8")
            return CompletedProcess(args, 0, "Successfully built wheel\n", "")
        if cwd == repo_root / "cli" and args[:3] == ["uvx", "twine", "check"]:
            return CompletedProcess(args, 0, "PASSED\n", "")
        if cwd == repo_root / "website" and args == ["pnpm", "build"]:
            return CompletedProcess(args, 0, "build complete\n", "")
        raise AssertionError(f"Unexpected command: cwd={cwd} args={args}")

    results = release_assistant.verify_release("0.2.0", repo_root=repo_root, runner=fake_runner)

    assert all(result.status != "FAIL" for result in results)
    assert smoke_installs
    assert smoke_installs[0].name == "dbt_forge-0.2.0-py3-none-any.whl"
    assert smoke_installs[0].parent.name == "dist"
