---
title: update
description: Command reference for re-applying dbt-forge templates to an existing project.
---

`dbt-forge update` re-renders the dbt-forge templates using the stored project
configuration and shows unified diffs for any files that have changed. Use it after
upgrading dbt-forge to pick up template improvements.

## Command

```bash
dbt-forge update [--dry-run]
```

## What it does

The command:

1. Reads the `.dbt-forge.yml` manifest written during `init`
2. Reconstructs the original `ProjectConfig` from the manifest
3. Re-renders all templates with the current version of dbt-forge
4. Compares each rendered file against the on-disk version
5. Reports counts of unchanged, changed, and new files

In interactive mode (default), each changed file is shown as a unified diff and you
can accept or skip the update. In `--dry-run` mode, only the diff summary is printed.

## Options

### `--dry-run`

Preview changes without writing anything. Shows the list of changed and new files
with their diffs.

```bash
dbt-forge update --dry-run
```

## Manifest

The `.dbt-forge.yml` file is created automatically when you run `dbt-forge init`.
It stores:

- `dbt_forge_version` — the version of dbt-forge that generated the project
- `created_at` — ISO timestamp of generation
- `config` — serialized `ProjectConfig` (adapter, marts, packages, feature flags)
- `files` — map of relative file paths to SHA-256 content hashes

The manifest is required for `update` to work. Projects created before this feature
was added will need to be re-generated with `init` to get a manifest.

## Output

```
  dbt-forge update — my_dbt_project

  22 unchanged
  2 changed
  0 new

Changed files:
  M  README.md
  M  .github/workflows/dbt_ci.yml
```

In interactive mode, each changed file shows a syntax-highlighted unified diff followed
by a prompt:

```
--- README.md ---
@@ -1,4 +1,5 @@
 # my_dbt_project
+
 ## Setup
-Run dbt debug to verify.
+Run `uv run --env-file .env dbt debug` to verify.

? Apply changes to README.md?
> accept
  skip
```

Select **accept** to overwrite the file with the new version, or **skip** to leave it
unchanged. After all files are reviewed, the manifest is updated to reflect the current
state.

## Behavior and limits

- Must run from inside an existing dbt project with a `.dbt-forge.yml` manifest.
- Only files tracked in the manifest are compared. Files added after `init` (via `add` commands or manually) are not affected.
- Accepted changes overwrite the on-disk file. Skipped changes leave the file unchanged.
- The manifest is updated after changes are applied.
- Does not require a warehouse connection.
