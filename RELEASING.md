# Releasing `dbt-forge`

This project ships its first public alpha release as the Python CLI package `dbt-forge`
version `0.1.0`.

## Scope

- Shipped artifact: the `dbt-forge` CLI package published to PyPI
- Source of truth for release notes: repository [`CHANGELOG.md`](CHANGELOG.md)
- Publish mechanism: GitHub Actions `Release` workflow on `v*` tags
- Website role: docs and marketing for the CLI; it is deployed separately and is not a
  separately versioned release artifact

## Verified prerequisites

Verified on March 8, 2026 from the local environment:

- GitHub repo: [`maroil/dbt-forge`](https://github.com/maroil/dbt-forge)
- Repository visibility: public
- Default branch: `main`
- GitHub environments present: `pypi`, `testpypi`
- Current package version in source: `0.1.0`
- PyPI JSON endpoint for `dbt-forge` currently returns `404`:
  `https://pypi.org/pypi/dbt-forge/json`
  Inference: the package name was not yet published on PyPI at verification time.

## Manual prerequisites

These cannot be fully verified from the repo alone and must be confirmed before tagging:

- Trusted Publishing is configured in PyPI for `maroil/dbt-forge` -> environment `pypi`
- Trusted Publishing is configured in TestPyPI for `maroil/dbt-forge` -> environment
  `testpypi`
- The release commit is merged to a clean `main` branch
- The website worktree changes that are not part of the release are either committed
  separately or left out of the release branch/tag

## Release candidate checks

Run these on the exact commit that will become the release candidate:

```bash
cd cli
uv run ruff check .
uv run pytest
uv build
uvx twine check dist/*
```

Smoke-test the built wheel with a supported interpreter (`3.11+`):

```bash
cd cli
tmpdir=$(mktemp -d)
python3.12 -m venv "$tmpdir/venv"
. "$tmpdir/venv/bin/activate"
python -m pip install --upgrade pip
pip install dist/*.whl
dbt-forge --version
dbt-forge --help
```

Website checks:

```bash
cd website
pnpm build
pnpm audit --prod --audit-level moderate
```

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
2. Ensure the release commit is on clean `main`.
3. Run the manual `Release` workflow with `workflow_dispatch` to publish to TestPyPI.
4. Verify the TestPyPI artifact by installing it or by re-testing the built wheel and
   checking `dbt-forge --version` and `dbt-forge --help`.
5. Create and push tag `v0.1.0`.
6. Let GitHub Actions publish to PyPI from the tag.
7. Create the GitHub Release using the `0.1.0` changelog entry.
