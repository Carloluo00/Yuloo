import unittest

import main
import s03_todo_write
import s04_subagents
import s05_skill_loading
import tools


class ConfigTests(unittest.TestCase):
    def test_shared_config_is_exposed_through_runtime_modules(self):
        import config

        self.assertEqual(s03_todo_write.MODEL, config.DEFAULT_MODEL)
        self.assertEqual(s04_subagents.MODEL, config.DEFAULT_MODEL)
        self.assertEqual(s05_skill_loading.MODEL, config.DEFAULT_MODEL)
        self.assertEqual(tools.MODEL, config.DEFAULT_MODEL)
        self.assertEqual(main.MODEL, config.DEFAULT_MODEL)
        self.assertEqual(s03_todo_write.TODO_REMINDER_INTERVAL, config.TODO_REMINDER_INTERVAL)
        self.assertEqual(s04_subagents.TODO_REMINDER_MESSAGE, config.TODO_REMINDER_MESSAGE)

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


if __name__ == "__main__":
    unittest.main()
