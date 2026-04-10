import shutil
import unittest
from uuid import uuid4
from pathlib import Path

import conftest


class PytestCachePolicyTests(unittest.TestCase):
    def test_pytest_ini_moves_cache_dir_under_tests(self):
        pytest_ini = Path("pytest.ini").read_text(encoding="utf-8")

        self.assertIn("[pytest]", pytest_ini)
        self.assertIn("cache_dir = tests/.pytest_cache", pytest_ini)
        self.assertIn("addopts = -p no:cacheprovider", pytest_ini)
        self.assertIn("norecursedirs = .* __pycache__ pytest-cache-files-*", pytest_ini)

    def test_cleanup_pytest_artifacts_only_removes_cache_targets(self):
        root = Path("tests") / f"_cache_policy_{uuid4().hex}"
        root.mkdir()
        try:
            cache_dir = root / ".pytest_cache"
            temp_dir = root / "pytest-cache-files-123"
            keep_dir = root / "keep-me"

            cache_dir.mkdir()
            temp_dir.mkdir()
            keep_dir.mkdir()
            (keep_dir / "note.txt").write_text("still here", encoding="utf-8")

            conftest.cleanup_pytest_artifacts(root)

            self.assertFalse(cache_dir.exists())
            self.assertFalse(temp_dir.exists())
            self.assertTrue(keep_dir.exists())
            self.assertTrue((keep_dir / "note.txt").exists())
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_cleanup_pytest_artifacts_ignores_missing_paths(self):
        root = Path("tests") / f"_cache_policy_{uuid4().hex}"
        root.mkdir()
        try:
            conftest.cleanup_pytest_artifacts(root)

            self.assertEqual(list(root.iterdir()), [])
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
