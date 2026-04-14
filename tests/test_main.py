import unittest
from unittest.mock import patch

import main
import s08_hook
import utils
from config import WORKDIR


class MainRuntimeTests(unittest.TestCase):
    def test_main_uses_s08_hook_runtime_by_default(self):
        self.assertEqual(main.MODEL, s08_hook.MODEL)
        self.assertEqual(main.agent_loop.__module__, s08_hook.__name__)

    def test_cli_prompt_uses_user_label(self):
        self.assertEqual(main.PROMPT, "\033[36muser >> \033[0m")

    def test_main_uses_dedicated_workspace_for_banner_and_log_metadata(self):
        with patch.object(main, "create_session_log_file", return_value="logs/test.jsonl") as create_log, patch.object(
            main, "print_banner"
        ) as print_banner, patch.object(main, "append_session_log"), patch.object(
            main, "print_status"
        ), patch.object(main.os, "chdir") as change_dir, patch("builtins.input", side_effect=["exit"]):
            main.run_cli()

        change_dir.assert_called_once_with(WORKDIR)
        self.assertEqual(create_log.call_args.kwargs["cwd"], str(WORKDIR))
        self.assertEqual(print_banner.call_args.args[1], str(WORKDIR))

    def test_run_cli_reuses_one_permission_manager_across_turns(self):
        perms_instance = object()
        hooks_instance = object()

        with patch.object(main, "PermissionManager", return_value=perms_instance) as build_perms, patch.object(
            main, "HookManager", return_value=hooks_instance
        ) as build_hooks, patch.object(
            main, "create_session_log_file", return_value="logs/test.jsonl"
        ), patch.object(main, "print_banner"), patch.object(main, "append_session_log"), patch.object(
            main, "print_status"
        ), patch.object(main, "print_assistant_reply"), patch.object(
            main, "count_available_skills", return_value=0
        ), patch.object(main.os, "chdir"), patch.object(
            main, "handle_builtin_command", return_value=False
        ), patch.object(
            main, "agent_loop", side_effect=["first reply", "second reply"]
        ) as run_loop, patch(
            "builtins.input", side_effect=["first task", "second task", "exit"]
        ):
            main.run_cli()

        build_perms.assert_called_once_with()
        build_hooks.assert_called_once_with()
        self.assertEqual(run_loop.call_count, 2)
        self.assertIs(run_loop.call_args_list[0].kwargs["perms"], perms_instance)
        self.assertIs(run_loop.call_args_list[1].kwargs["perms"], perms_instance)
        self.assertIs(run_loop.call_args_list[0].kwargs["hooks"], hooks_instance)
        self.assertIs(run_loop.call_args_list[1].kwargs["hooks"], hooks_instance)

    def test_skills_command_displays_available_skills_and_logs_event(self):
        with patch.object(utils, "print_skills") as print_skills, patch.object(utils, "append_session_log") as log_event:
            handled = main.handle_builtin_command(
                "/skills",
                [],
                "logs/test.jsonl",
                model=main.MODEL,
                runtime_name=main.RUNTIME_NAME,
                available_skills_text="- planner: Plans work",
                cwd=str(WORKDIR),
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
