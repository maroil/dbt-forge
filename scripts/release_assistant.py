#!/usr/bin/env python3
"""Repo entrypoint for the dbt-forge release assistant."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_SRC = REPO_ROOT / "cli" / "src"
if str(CLI_SRC) not in sys.path:
    sys.path.insert(0, str(CLI_SRC))

from dbt_forge.release_assistant import main


if __name__ == "__main__":
    raise SystemExit(main())
