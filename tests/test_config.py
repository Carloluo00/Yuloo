import unittest

import main
import s03_todo_write
import s04_subagents
import s05_skill_loading
import s06_compact
import s07_permission
import s08_hook
import tools


class ConfigTests(unittest.TestCase):
    def test_shared_config_is_exposed_through_runtime_modules(self):
        import config

        self.assertEqual(config.WORKDIR.name, "YULOO_WORKSPACE")
        self.assertTrue(config.WORKDIR.is_absolute())
        self.assertEqual(config.SKILLS_DIR, config.PROJECT_ROOT / "skills")
        self.assertEqual(config.LOG_DIR, config.PROJECT_ROOT / "logs")
        self.assertEqual(s03_todo_write.MODEL, config.DEFAULT_MODEL)
        self.assertEqual(s04_subagents.MODEL, config.DEFAULT_MODEL)
        self.assertEqual(s05_skill_loading.MODEL, config.DEFAULT_MODEL)
        self.assertEqual(s06_compact.MODEL, config.DEFAULT_MODEL)
        self.assertEqual(s07_permission.MODEL, config.DEFAULT_MODEL)
        self.assertEqual(s08_hook.MODEL, config.DEFAULT_MODEL)
        self.assertEqual(tools.MODEL, config.DEFAULT_MODEL)
        self.assertEqual(main.MODEL, config.DEFAULT_MODEL)
        self.assertEqual(s03_todo_write.TODO_REMINDER_INTERVAL, config.TODO_REMINDER_INTERVAL)
        self.assertEqual(s04_subagents.TODO_REMINDER_MESSAGE, config.TODO_REMINDER_MESSAGE)
        self.assertEqual(s06_compact.TODO_REMINDER_MESSAGE, config.TODO_REMINDER_MESSAGE)
        self.assertEqual(s07_permission.TODO_REMINDER_MESSAGE, config.TODO_REMINDER_MESSAGE)

    def test_system_prompts_are_built_from_config_helpers(self):
        import config

        workdir = config.WORKDIR
        self.assertEqual(
            s03_todo_write.SYSTEM,
            config.build_s03_system(workdir),
        )
        self.assertEqual(
            s04_subagents.SYSTEM,
            config.build_s04_system(workdir),
        )
        self.assertEqual(
            tools.SUBAGENT_SYSTEM,
            config.build_subagent_system(workdir),
        )
        self.assertIn(
            "Use load_skill when a task needs specialized instructions",
            config.build_s05_system(),
        )
        self.assertIn(
            "Keep long-running conversations compact",
            config.build_s06_system(workdir),
        )
        self.assertIn(
            "Some tool calls require permission",
            config.build_s07_system(workdir),
        )
        self.assertIn(
            "Some tool calls require permission",
            s08_hook.SYSTEM,
        )


if __name__ == "__main__":
    unittest.main()
