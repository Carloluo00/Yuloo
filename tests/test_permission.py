import unittest
from unittest.mock import patch

import permission


class PermissionManagerTests(unittest.TestCase):
    def test_auto_mode_allows_read_only_tools_and_asks_for_writes(self):
        manager = permission.PermissionManager(mode="auto")

        self.assertEqual(
            manager.check("read_file", {"path": "README.md"})["behavior"],
            "allow",
        )
        self.assertEqual(
            manager.check("load_skill", {"name": "planner"})["behavior"],
            "allow",
        )
        self.assertEqual(
            manager.check("todo", {"items": []})["behavior"],
            "allow",
        )
        self.assertEqual(
            manager.check("write_file", {"path": "out.txt", "content": "x"})["behavior"],
            "ask",
        )
        self.assertEqual(
            manager.check("task", {"prompt": "change files"})["behavior"],
            "ask",
        )

    def test_plan_mode_blocks_write_like_tools(self):
        manager = permission.PermissionManager(mode="plan")

        self.assertEqual(
            manager.check("write_file", {"path": "out.txt", "content": "x"})["behavior"],
            "deny",
        )
        self.assertEqual(
            manager.check("task", {"prompt": "change files"})["behavior"],
            "deny",
        )
        self.assertEqual(
            manager.check("read_file", {"path": "README.md"})["behavior"],
            "allow",
        )

    def test_bash_validator_denies_severe_patterns(self):
        manager = permission.PermissionManager()

        decision = manager.check("bash", {"command": "sudo dir"})

        self.assertEqual(decision["behavior"], "deny")
        self.assertIn("Bash validator", decision["reason"])

    def test_always_for_bash_scopes_rule_to_exact_command(self):
        manager = permission.PermissionManager()

        with patch("builtins.input", return_value="always"):
            approved = manager.ask_user("bash", {"command": "dir workspaceforagent"})

        self.assertTrue(approved)
        self.assertTrue(
            any(
                rule["tool"] == "bash"
                and rule.get("content") == "dir workspaceforagent"
                and rule["behavior"] == "allow"
                for rule in manager.rules
            )
        )
        self.assertEqual(
            manager.check("bash", {"command": "dir workspaceforagent"})["behavior"],
            "allow",
        )

    def test_always_for_flagged_bash_command_skips_repeat_prompt(self):
        manager = permission.PermissionManager()

        with patch("builtins.input", return_value="always"):
            approved = manager.ask_user("bash", {"command": "dir | findstr py"})

        self.assertTrue(approved)
        self.assertEqual(
            manager.check("bash", {"command": "dir | findstr py"})["behavior"],
            "allow",
        )
        self.assertEqual(
            manager.check("bash", {"command": "dir | findstr md"})["behavior"],
            "ask",
        )

    def test_severe_bash_validator_still_denies_even_with_allow_rule(self):
        manager = permission.PermissionManager(
            rules=list(permission.DEFAULT_RULES)
            + [{"tool": "bash", "content": "sudo dir", "behavior": "allow"}]
        )

        decision = manager.check("bash", {"command": "sudo dir"})

        self.assertEqual(decision["behavior"], "deny")
        self.assertIn("Bash validator", decision["reason"])


if __name__ == "__main__":
    unittest.main()
