# Releasing `dbt-forge`

This project is preparing the Python CLI package release `dbt-forge` version `0.3.0`.

## Release assistant

Run these commands from the repository root:

```bash
python3 scripts/release_assistant.py prepare 0.3.0
python3 scripts/release_assistant.py verify 0.3.0
python3 scripts/release_assistant.py publish 0.3.0 --confirm
```

`prepare` stages the version and changelog updates. `verify` is the release gate and fails on a
dirty worktree, a branch other than `main`, or a `main` branch that is not aligned with
`origin/main`. `publish` reruns `verify`, dispatches the TestPyPI workflow, waits for manual
confirmation, then creates and pushes the release tag and GitHub Release.

## Scope

- Shipped artifact: the `dbt-forge` CLI package published to PyPI
- Source of truth for release notes: repository [`CHANGELOG.md`](CHANGELOG.md)
- Publish mechanism: GitHub Actions `Release` workflow on `v*` tags
- Website role: docs and marketing for the CLI; it is deployed separately and is not a
  separately versioned release artifact

## Verified prerequisites

Verified on 2026-03-08 from the local environment:

- GitHub repo: [`maroil/dbt-forge`](https://github.com/maroil/dbt-forge)
- Repository visibility: public
- Default branch: `main`
- GitHub environments present: `pypi`, `testpypi`
- Current package version in source: `0.3.0`

## Manual prerequisites

These cannot be fully verified from the repo alone and must be confirmed before tagging:

- Trusted Publishing is configured in PyPI for `maroil/dbt-forge` -> environment `pypi`
- Trusted Publishing is configured in TestPyPI for `maroil/dbt-forge` -> environment
  `testpypi`
- The release commit is merged to a clean `main` branch
- The GitHub `Release` workflow still publishes `workflow_dispatch` runs to TestPyPI and `v*`
  tag pushes to PyPI
- The website worktree changes that are not part of the release are either committed separately
  or left out of the release branch/tag

## Release candidate checks

Run `python3 scripts/release_assistant.py verify 0.3.0` on the exact commit that will become
the release candidate. It performs these checks:

- clean worktree and `main` branch alignment with `origin/main`
- version consistency across `cli/src/dbt_forge/__init__.py`, `README.md`, `RELEASING.md`, and
  the released `CHANGELOG.md` section
- `uv run ruff check .`
- `uv run pytest`
- `uv build --clear --out-dir <temp>/dist`
- `uvx twine check <temp>/dist/*`
- wheel smoke install using only the target wheel
- `pnpm build` for `website/`

Website build warnings are reported as `WARN` but do not block the package release.

## Security notes

- Treat the shipped package environment as the release gate, not the transient environment
  created by an audit tool.
- During release prep, `pip-audit` reported `filelock` advisories from its own ephemeral
  environment while `uv tree --all-groups` showed no vulnerable `filelock` in the
  `dbt-forge` runtime dependency tree.
- If a future audit finding appears, trace it to one of:
  - runtime dependency of `dbt-forge`
  - dev-only dependency in `cli` tooling
  - audit tool bootstrap environment

Only runtime or intentional release-environment findings should block the package release.

## Publish sequence

1. Finalize `CHANGELOG.md` and release-facing docs.
2. Review the `prepare` diff, commit it, and merge it to clean `main`.
3. Run `python3 scripts/release_assistant.py verify 0.3.0`.
4. Run `python3 scripts/release_assistant.py publish 0.3.0 --confirm`.
5. Let the script create and push tag `v0.3.0`.
6. Let GitHub Actions publish to PyPI from the tag.
7. Create the GitHub Release using the `0.3.0` changelog entry.
