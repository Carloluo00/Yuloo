import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

import permission
import s07_permission as module


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


class PermissionRuntimeTests(unittest.TestCase):
    def test_agent_loop_uses_default_permission_manager_for_safe_read(self):
        conversation = [{"role": "user", "content": "Read the file"}]
        client = FakeClient(
            [
                make_response(
                    [
                        make_block(
                            "function_call",
                            name="read_file",
                            arguments='{"path":"README.md"}',
                            call_id="c1",
                        )
                    ]
                ),
                make_response([make_block("message", text="done")], output_text="done"),
            ]
        )

        with patch.object(module, "client", client), patch.object(module, "print_status"), patch.object(
            module, "print_assistant_reply"
        ), patch.object(module, "append_session_log"), patch.object(
            module, "run_tool_call", return_value="read ok"
        ) as run_tool, patch.object(
            module, "maybe_compact_history", side_effect=lambda conversation, state, log_path=None: conversation
        ), patch.object(module, "micro_compact", side_effect=lambda conversation: conversation):
            result = module.agent_loop(conversation, render_final=False, log_path="logs/test.jsonl")

        self.assertEqual(result, "done")
        run_tool.assert_called_once()
        tool_output = next(item for item in conversation if item.get("type") == "function_call_output")
        self.assertEqual(tool_output["output"], "read ok")

    def test_agent_loop_records_denied_permission_without_running_tool(self):
        conversation = [{"role": "user", "content": "Run a dangerous command"}]
        client = FakeClient(
            [
                make_response(
                    [
                        make_block(
                            "function_call",
                            name="bash",
                            arguments='{"command":"sudo dir"}',
                            call_id="c1",
                        )
                    ]
                ),
                make_response([make_block("message", text="done")], output_text="done"),
            ]
        )
        perms = permission.PermissionManager()

        with patch.object(module, "client", client), patch.object(module, "print_status"), patch.object(
            module, "print_assistant_reply"
        ), patch.object(module, "append_session_log"), patch.object(
            module, "run_tool_call"
        ) as run_tool, patch.object(
            module, "maybe_compact_history", side_effect=lambda conversation, state, log_path=None: conversation
        ), patch.object(module, "micro_compact", side_effect=lambda conversation: conversation):
            result = module.agent_loop(
                conversation,
                render_final=False,
                log_path="logs/test.jsonl",
                perms=perms,
            )

        self.assertEqual(result, "done")
        run_tool.assert_not_called()
        tool_output = next(item for item in conversation if item.get("type") == "function_call_output")
        self.assertIn("Permission denied:", tool_output["output"])


if __name__ == "__main__":
    unittest.main()
