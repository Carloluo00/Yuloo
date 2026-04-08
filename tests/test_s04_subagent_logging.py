import json
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

import tools


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


class SubagentLoggingTests(unittest.TestCase):
    def test_task_logs_subagent_lifecycle_and_tool_results(self):
        client = FakeClient(
            [
                make_response(
                    [
                        make_block(
                            "function_call",
                            name="bash",
                            arguments='{"command":"echo delegated"}',
                            call_id="sub-call-1",
                        )
                    ]
                ),
                make_response(
                    [
                        make_block(
                            "message",
                            content=[SimpleNamespace(type="output_text", text="delegated summary")],
                        )
                    ],
                    output_text="delegated summary",
                ),
            ]
        )
        task_block = make_block(
            "function_call",
            name="task",
            arguments=json.dumps({"prompt": "inspect repo", "description": "explore files"}),
            call_id="parent-call-1",
        )
        logged_events = []

        def fake_log(event, payload, log_path):
            logged_events.append((event, payload, log_path))

        with patch.object(tools, "client", client), patch.object(tools, "append_session_log", side_effect=fake_log), patch.object(
            tools, "print_status"
        ), patch.dict(tools.TOOL_HANDLERS, {"bash": lambda command: f"ran {command}"}, clear=False):
            output = tools.run_tool_call(task_block, "logs/test.jsonl")

        self.assertEqual(output, "delegated summary")
        event_names = [event for event, _, _ in logged_events]
        self.assertIn("subagent_started", event_names)
        self.assertIn("subagent_response", event_names)
        self.assertIn("subagent_tool_result", event_names)
        self.assertIn("subagent_finished", event_names)

        start_payload = next(payload for event, payload, _ in logged_events if event == "subagent_started")
        self.assertEqual(start_payload["parent_call_id"], "parent-call-1")
        self.assertEqual(start_payload["description"], "explore files")

        tool_payload = next(payload for event, payload, _ in logged_events if event == "subagent_tool_result")
        self.assertEqual(tool_payload["parent_call_id"], "parent-call-1")
        self.assertEqual(tool_payload["name"], "bash")
        self.assertEqual(tool_payload["args"], {"command": "echo delegated"})
        self.assertEqual(tool_payload["output"], "ran echo delegated")

        finish_payload = next(payload for event, payload, _ in logged_events if event == "subagent_finished")
        self.assertEqual(finish_payload["parent_call_id"], "parent-call-1")
        self.assertEqual(finish_payload["summary"], "delegated summary")

    def test_subagent_response_events_include_each_turn(self):
        client = FakeClient(
            [
                make_response(
                    [
                        make_block(
                            "function_call",
                            name="read_file",
                            arguments='{"path":"README.md"}',
                            call_id="sub-call-1",
                        )
                    ]
                ),
                make_response(
                    [
                        make_block(
                            "message",
                            content=[SimpleNamespace(type="output_text", text="done")],
                        )
                    ],
                    output_text="done",
                ),
            ]
        )
        logged_events = []

        def fake_log(event, payload, log_path):
            logged_events.append((event, payload, log_path))

        with patch.object(tools, "client", client), patch.object(tools, "append_session_log", side_effect=fake_log), patch.object(
            tools, "print_status"
        ), patch.dict(tools.TOOL_HANDLERS, {"read_file": lambda path, limit=None: "file content"}, clear=False):
            summary = tools.run_subagent(
                "read the readme",
                log_path="logs/test.jsonl",
                parent_call_id="parent-call-2",
                description="read docs",
            )

        self.assertEqual(summary, "done")
        response_payloads = [payload for event, payload, _ in logged_events if event == "subagent_response"]
        self.assertEqual(len(response_payloads), 2)
        self.assertEqual([payload["turn"] for payload in response_payloads], [1, 2])
        self.assertTrue(all(payload["parent_call_id"] == "parent-call-2" for payload in response_payloads))

    def test_task_subagent_inherits_parent_conversation_before_prompt(self):
        client = FakeClient(
            [
                make_response(
                    [
                        make_block(
                            "message",
                            content=[SimpleNamespace(type="output_text", text="delegated summary")],
                        )
                    ],
                    output_text="delegated summary",
                )
            ]
        )
        parent_conversation = [
            {"role": "user", "content": "Parent request"},
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "Parent context"}],
            },
            {
                "type": "function_call_output",
                "call_id": "todo-call-1",
                "output": "[ ] #1: delegated task",
            },
        ]
        task_block = make_block(
            "function_call",
            name="task",
            arguments=json.dumps(
                {
                    "prompt": "Only inspect README and summarize the delegation-relevant parts.",
                    "description": "inspect docs",
                }
            ),
            call_id="parent-call-3",
        )

        with patch.object(tools, "client", client), patch.object(tools, "print_status"):
            output = tools.run_tool_call(task_block, None, parent_conversation=parent_conversation)

        self.assertEqual(output, "delegated summary")
        self.assertEqual(len(client.responses.calls), 1)
        subagent_input = client.responses.calls[0]["input"]
        self.assertEqual(subagent_input[:-1], parent_conversation)
        self.assertEqual(
            subagent_input[-1],
            {
                "role": "user",
                "content": "Only inspect README and summarize the delegation-relevant parts.",
            },
        )
        self.assertIsNot(subagent_input, parent_conversation)
        self.assertEqual(parent_conversation[-1]["output"], "[ ] #1: delegated task")


if __name__ == "__main__":
    unittest.main()
