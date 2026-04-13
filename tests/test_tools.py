import shutil
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import config
import tools


def get_tool(name: str):
    return next(tool_def for tool_def in tools.TOOLS if tool_def["name"] == name)


class TodoToolTests(unittest.TestCase):
    def setUp(self):
        self.manager = tools.TodoManager()
        self.tmp_root = Path("tests") / "_tmp_tool_persist"
        shutil.rmtree(self.tmp_root, ignore_errors=True)
        self.tmp_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmp_root, ignore_errors=True)

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

    def test_run_tool_call_persists_large_output(self):
        block = SimpleNamespace(
            type="function_call",
            name="bash",
            arguments='{"command":"dir"}',
            call_id="persist-call-1",
        )
        outputs_dir = self.tmp_root / ".task_outputs" / "tool-results"

        with patch.object(tools, "WORKDIR", self.tmp_root), patch.object(
            tools, "TOOL_RESULTS_DIR", outputs_dir
        ), patch.object(tools, "PERSIST_THRESHOLD", 10), patch.object(
            tools, "PREVIEW_CHARS", 5
        ), patch.object(tools, "print_status"), patch.dict(
            tools.TOOL_HANDLERS, {"bash": lambda command: "A" * 50}, clear=False
        ):
            output = tools.run_tool_call(block, None)

        stored_path = outputs_dir / "persist-call-1.txt"
        self.assertTrue(stored_path.exists())
        self.assertEqual(stored_path.read_text(encoding="utf-8"), "A" * 50)
        self.assertIn("<persisted-output>", output)
        self.assertIn("AAAAA", output)

    def test_run_tool_call_does_not_repersist_reads_from_tool_results_dir(self):
        block = SimpleNamespace(
            type="function_call",
            name="read_file",
            arguments='{"path":".task_outputs/tool-results/saved.txt"}',
            call_id="persist-call-2",
        )
        outputs_dir = self.tmp_root / ".task_outputs" / "tool-results"
        outputs_dir.mkdir(parents=True, exist_ok=True)
        saved_path = outputs_dir / "saved.txt"
        saved_path.write_text("B" * 50, encoding="utf-8")

        with patch.object(tools, "WORKDIR", self.tmp_root), patch.object(
            tools, "TOOL_RESULTS_DIR", outputs_dir
        ), patch.object(tools, "PERSIST_THRESHOLD", 10), patch.object(
            tools, "print_status"
        ), patch.dict(
            tools.TOOL_HANDLERS, {"read_file": lambda path, limit=None: "B" * 50}, clear=False
        ):
            output = tools.run_tool_call(block, None)

        self.assertEqual(output, "B" * 50)
        self.assertFalse((outputs_dir / "persist-call-2.txt").exists())

    def test_update_accepts_json_encoded_array_string(self):
        output = self.manager.update(
            '[{"id":"1","text":"first","status":"in_progress"},{"id":"2","text":"second","status":"pending"}]'
        )

        self.assertIn("[>] #1: first", output)
        self.assertIn("[ ] #2: second", output)
        self.assertEqual(len(self.manager.items), 2)

    def test_update_renders_completed_items_with_check_mark(self):
        output = self.manager.update(
            [{"id": "1", "text": "first", "status": "completed"}]
        )

        self.assertIn("[✓] #1: first", output)
        self.assertNotIn("[x] #1: first", output)

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

    def test_run_write_uses_utf8_encoding(self):
        target = self.tmp_root / "write-target.txt"

        with patch.object(tools, "safe_path", return_value=target), patch(
            "pathlib.Path.write_text",
            autospec=True,
            return_value=len("你好"),
        ) as write_text:
            result = tools.run_write("write-target.txt", "你好")

        self.assertEqual(result, "Wrote 2 bytes to write-target.txt")
        self.assertEqual(write_text.call_args.kwargs["encoding"], "utf-8")

    def test_run_edit_uses_explicit_utf8_for_utf8_files(self):
        target = self.tmp_root / "README.zh-CN.md"
        written = {}

        def fake_read_text(path_obj, *args, **kwargs):
            self.assertEqual(path_obj, target)
            self.assertEqual(kwargs.get("encoding"), "utf-8")
            return "prefix old suffix"

        def fake_write_text(path_obj, content, *args, **kwargs):
            written["path"] = path_obj
            written["content"] = content
            written["encoding"] = kwargs.get("encoding")
            return len(content)

        with patch.object(tools, "safe_path", return_value=target), patch(
            "pathlib.Path.read_text",
            autospec=True,
            side_effect=fake_read_text,
        ), patch(
            "pathlib.Path.write_text",
            autospec=True,
            side_effect=fake_write_text,
        ):
            result = tools.run_edit("README.zh-CN.md", "old", "new")

        self.assertEqual(result, "Edited README.zh-CN.md")
        self.assertEqual(written["path"], target)
        self.assertEqual(written["content"], "prefix new suffix")
        self.assertEqual(written["encoding"], "utf-8")

    def test_run_edit_preserves_fallback_encoding_for_legacy_files(self):
        target = self.tmp_root / "legacy.txt"
        written = {}

        def fake_read_text(path_obj, *args, **kwargs):
            self.assertEqual(path_obj, target)
            if kwargs.get("encoding") == "utf-8":
                raise UnicodeDecodeError("utf-8", b"\x80", 0, 1, "bad start byte")
            self.assertEqual(kwargs.get("encoding"), "gbk")
            return "legacy old text"

        def fake_write_text(path_obj, content, *args, **kwargs):
            written["path"] = path_obj
            written["content"] = content
            written["encoding"] = kwargs.get("encoding")
            return len(content)

        with patch.object(tools, "safe_path", return_value=target), patch(
            "pathlib.Path.read_text",
            autospec=True,
            side_effect=fake_read_text,
        ), patch(
            "pathlib.Path.write_text",
            autospec=True,
            side_effect=fake_write_text,
        ):
            result = tools.run_edit("legacy.txt", "old", "new")

        self.assertEqual(result, "Edited legacy.txt")
        self.assertEqual(written["path"], target)
        self.assertEqual(written["content"], "legacy new text")
        self.assertEqual(written["encoding"], "gbk")

    def test_run_tool_call_returns_error_for_invalid_json_arguments(self):
        block = SimpleNamespace(
            type="function_call",
            name="read_file",
            arguments='{"path":',
            call_id="bad-json-call",
        )

        with patch.object(tools, "append_session_log") as log_event, patch.object(
            tools, "print_status"
        ) as show_status:
            output = tools.run_tool_call(block, "logs/test.jsonl")

        self.assertIn("Invalid tool arguments JSON", output)
        show_status.assert_called_once()
        log_event.assert_called_once()
        self.assertEqual(log_event.call_args.args[0], "tool_error")

    def test_skill_parser_accepts_crlf_frontmatter(self):
        registry = tools.SkillRegistry(self.tmp_root / "skills")

        meta, body = registry._parse_frontmatter(
            "---\r\nname: planner\r\ndescription: CRLF skill\r\n---\r\nbody line\r\n"
        )

        self.assertEqual(meta["name"], "planner")
        self.assertEqual(meta["description"], "CRLF skill")
        self.assertEqual(body, "body line\r\n")


if __name__ == "__main__":
    unittest.main()
