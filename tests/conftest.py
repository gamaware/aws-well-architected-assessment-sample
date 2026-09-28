from __future__ import annotations

import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def data_copy(tmp_path: Path) -> Path:
    """A writable copy of the repository's data and report, for tests that break the data on purpose."""
    root = tmp_path / "repo"
    shutil.copytree(REPO_ROOT / "data", root / "data")
    shutil.copytree(REPO_ROOT / "report", root / "report", ignore=shutil.ignore_patterns("*.pdf"))
    return root
