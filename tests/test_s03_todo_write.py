import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

import s03_todo_write as module


def make_block(block_type: str, **kwargs):
    return SimpleNamespace(type=block_type, **kwargs)


def make_response(output, output_text="", status="completed"):
    return SimpleNamespace(output=output, output_text=output_text, status=status)


class FakeResponses:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        snapshot = dict(kwargs)
        if "input" in snapshot:
            snapshot["input"] = deepcopy(snapshot["input"])
        self.calls.append(snapshot)
        return self._responses.pop(0)


class FakeClient:
    def __init__(self, responses):
        self.responses = FakeResponses(responses)


class AgentLoopTests(unittest.TestCase):
    def test_reminder_is_added_as_plain_user_message_after_three_non_todo_rounds(self):
        conversation = [{"role": "user", "content": "finish the task"}]
        client = FakeClient(
            [
                make_response([make_block("function_call", name="bash", arguments='{"command":"echo 1"}', call_id="c1")]),
                make_response([make_block("function_call", name="bash", arguments='{"command":"echo 2"}', call_id="c2")]),
                make_response([make_block("function_call", name="bash", arguments='{"command":"echo 3"}', call_id="c3")]),
                make_response([make_block("message", text="done")], output_text="done"),
            ]
        )

        with patch.object(module, "client", client), patch.object(module, "print_status"), patch.object(
            module, "print_assistant_reply"
        ), patch.object(module, "append_session_log"), patch.dict(
            module.TOOL_HANDLERS, {"bash": lambda command: f"ran {command}"}, clear=False
        ):
            result = module.agent_loop(conversation, render_final=False, log_path="logs/test.jsonl")

        self.assertEqual(result, "done")
        tool_outputs = [item for item in conversation if item.get("type") == "function_call_output"]
        self.assertEqual(len(tool_outputs), 3)
        reminder_messages = [
            item for item in conversation if item.get("role") == "user" and item.get("content") == module.TODO_REMINDER_MESSAGE
        ]
        self.assertEqual(len(reminder_messages), 1)
        self.assertFalse(
            any(item.get("role") == "user" and isinstance(item.get("content"), list) for item in conversation),
            "tool results should not be wrapped into a synthetic user message",
        )
        self.assertEqual(client.responses.calls[3]["input"][-1], {"role": "user", "content": module.TODO_REMINDER_MESSAGE})

    def test_tool_errors_are_returned_as_tool_output_instead_of_crashing(self):
        conversation = [{"role": "user", "content": "update todos"}]
        client = FakeClient(
            [
                make_response(
                    [
                        make_block(
                            "function_call",
                            name="todo",
                            arguments='{"items":[{"id":"1","text":"first","status":"in_progress"},{"id":"2","text":"second","status":"in_progress"}]}',
                            call_id="todo-1",
                        )
                    ]
                ),
                make_response([make_block("message", text="done")], output_text="done"),
            ]
        )
        logged_events = []

        def fake_log(event, payload, log_path):
            logged_events.append((event, payload, log_path))

        with patch.object(module, "client", client), patch.object(module, "print_status"), patch.object(
            module, "print_assistant_reply"
        ), patch.object(module, "append_session_log", side_effect=fake_log), patch.object(module, "print_todo_state"):
            result = module.agent_loop(conversation, render_final=False, log_path="logs/test.jsonl")

        self.assertEqual(result, "done")
        tool_output = next(item for item in conversation if item.get("type") == "function_call_output")
        self.assertIn("Error:", tool_output["output"])
        self.assertIn("only one in_progress entry", tool_output["output"])
        self.assertTrue(any(event == "tool_error" and payload["name"] == "todo" for event, payload, _ in logged_events))


if __name__ == "__main__":
    unittest.main()
