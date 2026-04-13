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
    def test_task_subagent_reuses_parent_permission_manager(self):
        task_block = make_block(
            "function_call",
            name="task",
            arguments=json.dumps({"prompt": "inspect repo", "description": "explore files"}),
            call_id="parent-call-0",
        )
        perms = object()

        with patch.object(tools, "run_subagent", return_value="delegated summary") as run_subagent, patch.object(
            tools, "print_status"
        ):
            output = tools.run_tool_call(task_block, None, perms=perms)

        self.assertEqual(output, "delegated summary")
        self.assertIs(run_subagent.call_args.kwargs["perms"], perms)

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

    def test_subagent_checks_permissions_before_running_child_tools(self):
        client = FakeClient(
            [
                make_response(
                    [
                        make_block(
                            "function_call",
                            name="bash",
                            arguments='{"command":"echo delegated"}',
                            call_id="sub-call-2",
                        )
                    ]
                ),
                make_response(
                    [
                        make_block(
                            "message",
                            content=[SimpleNamespace(type="output_text", text="blocked safely")],
                        )
                    ],
                    output_text="blocked safely",
                ),
            ]
        )
        logged_events = []

        class FakePerms:
            def __init__(self):
                self.ask_calls = []

            def check(self, tool_name, tool_args):
                if tool_name == "bash":
                    return {"behavior": "ask", "reason": "needs explicit approval"}
                return {"behavior": "allow", "reason": "safe"}

            def ask_user(self, tool_name, tool_args):
                self.ask_calls.append((tool_name, tool_args))
                return False

        perms = FakePerms()

        def fake_log(event, payload, log_path):
            logged_events.append((event, payload, log_path))

        with patch.object(tools, "client", client), patch.object(
            tools, "append_session_log", side_effect=fake_log
        ), patch.object(tools, "print_status"), patch.dict(
            tools.TOOL_HANDLERS,
            {"bash": lambda command: (_ for _ in ()).throw(AssertionError("bash should not run"))},
            clear=False,
        ):
            summary = tools.run_subagent(
                "inspect safely",
                log_path="logs/test.jsonl",
                parent_call_id="parent-call-4",
                description="inspect docs",
                perms=perms,
            )

        self.assertEqual(summary, "blocked safely")
        self.assertEqual(perms.ask_calls, [("bash", {"command": "echo delegated"})])
        permission_payload = next(
            payload for event, payload, _ in logged_events if event == "subagent_permission_decision"
        )
        self.assertEqual(permission_payload["tool"], "bash")
        self.assertEqual(permission_payload["behavior"], "ask")
        second_turn_input = client.responses.calls[1]["input"]
        denied_result = next(item for item in second_turn_input if item.get("type") == "function_call_output")
        self.assertEqual(denied_result["output"], "Permission denied by user for bash")

    def test_subagent_turn_survives_invalid_tool_arguments(self):
        client = FakeClient(
            [
                make_response(
                    [
                        make_block(
                            "function_call",
                            name="read_file",
                            arguments='{"path":',
                            call_id="sub-call-bad-json",
                        )
                    ]
                ),
                make_response(
                    [
                        make_block(
                            "message",
                            content=[SimpleNamespace(type="output_text", text="recovered")],
                        )
                    ],
                    output_text="recovered",
                ),
            ]
        )

        with patch.object(tools, "client", client), patch.object(tools, "append_session_log"), patch.object(
            tools, "print_status"
        ):
            summary = tools.run_subagent("inspect safely", log_path="logs/test.jsonl")

        self.assertEqual(summary, "recovered")
        second_turn_input = client.responses.calls[1]["input"]
        error_result = next(item for item in second_turn_input if item.get("type") == "function_call_output")
        self.assertIn("Invalid tool arguments JSON", error_result["output"])


if __name__ == "__main__":
    unittest.main()
