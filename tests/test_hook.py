import json
import shutil
import unittest
from pathlib import Path

from hook import HookManager


class HookManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp_root = Path("tests") / "_tmp_hooks"
        shutil.rmtree(self.tmp_root, ignore_errors=True)
        self.tmp_root.mkdir(parents=True, exist_ok=True)
        self.config_path = self.tmp_root / ".hooks.json"

    def tearDown(self):
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def write_config(self, payload: dict):
        self.config_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def test_run_hooks_uses_declarative_fields_without_running_commands(self):
        self.write_config(
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "read_file",
                            "log_message": "observed read",
                            "updated_args": {"path": "README.md"},
                            "additional_context": "Summarize the README after reading it.",
                            "permission_decision": {"behavior": "ask", "reason": "needs review"},
                        }
                    ]
                }
            }
        )
        manager = HookManager(config_path=self.config_path, sdk_mode=True)

        result = manager.run_hooks(
            "PreToolUse",
            {"tool_name": "read_file", "tool_args": {"path": "old.txt"}},
        )

        self.assertFalse(result["blocked"])
        self.assertEqual(result["updated_tool_args"], {"path": "README.md"})
        self.assertEqual(result["messages"], ["Summarize the README after reading it."])
        self.assertEqual(
            result["permission_override"],
            {"behavior": "ask", "reason": "needs review"},
        )

    def test_run_hooks_blocks_and_reports_reason_from_declarative_rule(self):
        self.write_config(
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "bash",
                            "block": True,
                            "block_reason": "bash is disabled in this workspace",
                        }
                    ]
                }
            }
        )
        manager = HookManager(config_path=self.config_path, sdk_mode=True)

        result = manager.run_hooks(
            "PreToolUse",
            {"tool_name": "bash", "tool_args": {"command": "dir"}},
        )

        self.assertTrue(result["blocked"])
        self.assertEqual(result["block_reason"], "bash is disabled in this workspace")
        self.assertIsNone(result["updated_tool_args"])
        self.assertEqual(result["messages"], [])
        self.assertIsNone(result["permission_override"])
