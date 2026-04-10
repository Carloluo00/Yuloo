import unittest
from types import SimpleNamespace
from unittest.mock import patch

import config
import tools


def get_tool(name: str):
    return next(tool_def for tool_def in tools.TOOLS if tool_def["name"] == name)


class TodoToolTests(unittest.TestCase):
    def setUp(self):
        self.manager = tools.TodoManager()

    def test_todo_tool_schema_warns_against_stringifying_items(self):
        todo_tool = get_tool("todo")

        self.assertIn("JSON array", todo_tool["description"])
        self.assertIn("never a quoted string", todo_tool["description"])
        self.assertNotIn(
            "Use the todo tool with items as a native JSON array",
            config.build_s03_system(config.WORKDIR),
        )
        self.assertNotIn(
            "Do not wrap todo.items in quotes",
            config.build_s04_system(config.WORKDIR),
        )

    def test_skill_tool_uses_singular_load_skill_name(self):
        skill_tool = get_tool("load_skill")

        self.assertEqual(skill_tool["name"], "load_skill")
        self.assertFalse(any(tool_def["name"] == "load_skills" for tool_def in tools.TOOLS))

    def test_run_tool_call_logs_skill_load_event(self):
        block = SimpleNamespace(
            type="function_call",
            name="load_skill",
            arguments='{"name":"planner"}',
            call_id="skill-call-1",
        )
        logged_events = []

        def fake_log(event, payload, log_path):
            logged_events.append((event, payload, log_path))

        with patch.object(tools.SKILL_REGISTRY, "load_full_text", return_value="<skill name=\"planner\">\nbody\n</skill>"), patch.object(
            tools, "append_session_log", side_effect=fake_log
        ), patch.object(tools, "print_status"), patch.object(tools, "print_skill_state"):
            output = tools.run_tool_call(block, "logs/test.jsonl")

        self.assertEqual(output, "<skill name=\"planner\">\nbody\n</skill>")
        self.assertTrue(
            any(
                event == "skill_loaded" and payload["name"] == "planner" and payload["ok"]
                for event, payload, _ in logged_events
            )
        )

    def test_update_accepts_json_encoded_array_string(self):
        output = self.manager.update(
            '[{"id":"1","text":"first","status":"in_progress"},{"id":"2","text":"second","status":"pending"}]'
        )

        self.assertIn("[>] #1: first", output)
        self.assertIn("[ ] #2: second", output)
        self.assertEqual(len(self.manager.items), 2)

    def test_update_rejects_unparseable_string_with_clear_error(self):
        with self.assertRaisesRegex(
            ValueError,
            "todo.items was a string but not valid JSON",
        ):
            self.manager.update("not json")

    def test_update_rejects_non_array_payload_with_clear_error(self):
        with self.assertRaisesRegex(
            ValueError,
            "todo.items must be a JSON array of todo objects, got dict",
        ):
            self.manager.update({"id": "1", "text": "first", "status": "pending"})

    def test_maybe_add_todo_reminder_injects_message_and_resets_counter(self):
        conversation = [{"role": "user", "content": "finish task"}]

        with patch.object(tools, "append_session_log") as log_event, patch.object(tools, "print_status") as show_status:
            rounds = tools.maybe_add_todo_reminder(
                conversation,
                rounds_since_todo=2,
                used_todo=False,
                log_path="logs/test.jsonl",
                reminder_interval=3,
                reminder_message="Reminder text",
            )

        self.assertEqual(rounds, 0)
        self.assertEqual(conversation[-1], {"role": "user", "content": "Reminder text"})
        show_status.assert_called_once_with("Injected todo reminder for the agent.", "33")
        log_event.assert_called_once_with(
            "todo_reminder",
            {"message": "Reminder text", "rounds_since_todo": 3},
            "logs/test.jsonl",
        )

    def test_maybe_add_todo_reminder_skips_injection_when_todo_was_used(self):
        conversation = [{"role": "user", "content": "finish task"}]

        with patch.object(tools, "append_session_log") as log_event, patch.object(tools, "print_status") as show_status:
            rounds = tools.maybe_add_todo_reminder(
                conversation,
                rounds_since_todo=2,
                used_todo=True,
                log_path="logs/test.jsonl",
                reminder_interval=3,
                reminder_message="Reminder text",
            )

        self.assertEqual(rounds, 0)
        self.assertEqual(len(conversation), 1)
        show_status.assert_not_called()
        log_event.assert_not_called()


if __name__ == "__main__":
    unittest.main()
