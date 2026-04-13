from __future__ import annotations

import shutil
from pathlib import Path

import pytest


ROOT_DIR = Path(__file__).resolve().parent
TESTS_DIR = ROOT_DIR / "tests"


def cleanup_pytest_artifacts(root: Path) -> None:
    # Tests are expected to leave the workspace clean between runs.
    targets = [root / ".pytest_cache", *root.glob("pytest-cache-files-*")]
    for target in targets:
        shutil.rmtree(target, ignore_errors=True)


def cleanup_workspace_pytest_artifacts() -> None:
    cleanup_pytest_artifacts(ROOT_DIR)
    cleanup_pytest_artifacts(TESTS_DIR)


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session) -> None:
    cleanup_workspace_pytest_artifacts()


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus: int) -> None:
    cleanup_workspace_pytest_artifacts()
