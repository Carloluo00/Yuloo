import unittest
from unittest.mock import patch

import main
import s06_compact
import utils


class MainRuntimeTests(unittest.TestCase):
    def test_main_uses_s06_compact_runtime_by_default(self):
        self.assertEqual(main.MODEL, s06_compact.MODEL)
        self.assertEqual(main.agent_loop.__module__, s06_compact.__name__)

    def test_cli_prompt_uses_user_label(self):
        self.assertEqual(main.PROMPT, "\033[36muser >> \033[0m")

    def test_skills_command_displays_available_skills_and_logs_event(self):
        with patch.object(utils, "print_skills") as print_skills, patch.object(utils, "append_session_log") as log_event:
            handled = main.handle_builtin_command(
                "/skills",
                [],
                "logs/test.jsonl",
                model=main.MODEL,
                runtime_name=main.RUNTIME_NAME,
                available_skills_text="- planner: Plans work",
                cwd="E:\\Project\\Yuloo",
            )

        self.assertTrue(handled)
        print_skills.assert_called_once_with("- planner: Plans work")
        log_event.assert_called_once_with(
            "skills_viewed",
            {"skills_available": 1},
            "logs/test.jsonl",
        )


if __name__ == "__main__":
    unittest.main()
