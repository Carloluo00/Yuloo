import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

import s08_hook as module
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


class HookRuntimeTests(unittest.TestCase):
    def test_session_start_hook_runs_only_once_when_reusing_same_hook_manager(self):
        conversation = [{"role": "user", "content": "first turn"}]
        first_client = FakeClient(
            [
                make_response([make_block("message", text="first done")], output_text="first done"),
            ]
        )
        second_client = FakeClient(
            [
                make_response([make_block("message", text="second done")], output_text="second done"),
            ]
        )

        class FakeHooks:
            def __init__(self):
                self.session_started = False
                self.session_start_calls = 0

            def run_hooks(self, event, context=None):
                if event == "SessionStart":
                    self.session_start_calls += 1
                    return {
                        "blocked": False,
                        "block_reason": None,
                        "updated_tool_args": None,
                        "messages": ["Session hook message"],
                        "permission_override": None,
                    }
                return {
                    "blocked": False,
                    "block_reason": None,
                    "updated_tool_args": None,
                    "messages": [],
                    "permission_override": None,
                }

        hooks = FakeHooks()

        with patch.object(module, "client", first_client), patch.object(module, "print_status"), patch.object(
            module, "print_assistant_reply"
        ), patch.object(module, "append_session_log"), patch.object(
            module, "maybe_compact_history", side_effect=lambda conversation, state, log_path=None: conversation
        ), patch.object(module, "micro_compact", side_effect=lambda conversation: conversation):
            first_result = module.agent_loop(
                conversation,
                render_final=False,
                log_path="logs/test.jsonl",
                hooks=hooks,
            )

        conversation.append({"role": "user", "content": "second turn"})
        with patch.object(module, "client", second_client), patch.object(module, "print_status"), patch.object(
            module, "print_assistant_reply"
        ), patch.object(module, "append_session_log"), patch.object(
            module, "maybe_compact_history", side_effect=lambda conversation, state, log_path=None: conversation
        ), patch.object(module, "micro_compact", side_effect=lambda conversation: conversation):
            second_result = module.agent_loop(
                conversation,
                render_final=False,
                log_path="logs/test.jsonl",
                hooks=hooks,
            )

        self.assertEqual(first_result, "first done")
        self.assertEqual(second_result, "second done")
        self.assertEqual(hooks.session_start_calls, 1)

    def test_session_start_hook_injects_message_before_first_model_turn(self):
        conversation = [{"role": "user", "content": "Help me"}]
        client = FakeClient(
            [
                make_response([make_block("message", text="done")], output_text="done"),
            ]
        )

        class FakeHooks:
            def run_hooks(self, event, context=None):
                if event == "SessionStart":
                    return {
                        "blocked": False,
                        "block_reason": None,
                        "updated_tool_args": None,
                        "messages": ["Hook note for the first turn"],
                        "permission_override": None,
                    }
                return {
                    "blocked": False,
                    "block_reason": None,
                    "updated_tool_args": None,
                    "messages": [],
                    "permission_override": None,
                }

        with patch.object(module, "client", client), patch.object(module, "print_status"), patch.object(
            module, "print_assistant_reply"
        ), patch.object(module, "append_session_log"), patch.object(
            module, "maybe_compact_history", side_effect=lambda conversation, state, log_path=None: conversation
        ), patch.object(module, "micro_compact", side_effect=lambda conversation: conversation):
            result = module.agent_loop(
                conversation,
                render_final=False,
                log_path="logs/test.jsonl",
                hooks=FakeHooks(),
            )

        self.assertEqual(result, "done")
        first_input = client.responses.calls[0]["input"]
        self.assertEqual(first_input[0], {"role": "user", "content": "Help me"})
        self.assertEqual(first_input[1]["role"], "user")
        self.assertIn("Hook note for the first turn", first_input[1]["content"])

    def test_pre_tool_hook_can_block_without_running_tool(self):
        conversation = [{"role": "user", "content": "Run a tool"}]
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

        class FakeHooks:
            def run_hooks(self, event, context=None):
                if event == "PreToolUse":
                    return {
                        "blocked": True,
                        "block_reason": "blocked by pre-tool hook",
                        "updated_tool_args": None,
                        "messages": [],
                        "permission_override": None,
                    }
                return {
                    "blocked": False,
                    "block_reason": None,
                    "updated_tool_args": None,
                    "messages": [],
                    "permission_override": None,
                }

        with patch.object(module, "client", client), patch.object(module, "print_status"), patch.object(
            module, "print_assistant_reply"
        ), patch.object(module, "append_session_log"), patch.object(
            tools, "run_tool_call"
        ) as run_tool, patch.object(
            module, "maybe_compact_history", side_effect=lambda conversation, state, log_path=None: conversation
        ), patch.object(module, "micro_compact", side_effect=lambda conversation: conversation):
            result = module.agent_loop(
                conversation,
                render_final=False,
                log_path="logs/test.jsonl",
                hooks=FakeHooks(),
            )

        self.assertEqual(result, "done")
        run_tool.assert_not_called()
        tool_output = next(item for item in conversation if item.get("type") == "function_call_output")
        self.assertEqual(tool_output["output"], "Blocked by hook: blocked by pre-tool hook")

    def test_pre_tool_hook_updates_args_before_permission_and_tool_execution(self):
        conversation = [{"role": "user", "content": "Read the file"}]
        client = FakeClient(
            [
                make_response(
                    [
                        make_block(
                            "function_call",
                            name="read_file",
                            arguments='{"path":"old.txt"}',
                            call_id="c1",
                        )
                    ]
                ),
                make_response([make_block("message", text="done")], output_text="done"),
            ]
        )
        checked = []
        asked = []

        class FakePerms:
            def check(self, tool_name, tool_args):
                checked.append((tool_name, dict(tool_args)))
                return {"behavior": "allow", "reason": "safe"}

            def ask_user(self, tool_name, tool_args):
                asked.append((tool_name, dict(tool_args)))
                return False

        class FakeHooks:
            def run_hooks(self, event, context=None):
                if event == "PreToolUse":
                    return {
                        "blocked": False,
                        "block_reason": None,
                        "updated_tool_args": {"path": "README.md"},
                        "messages": [],
                        "permission_override": {"behavior": "ask", "reason": "review first"},
                    }
                return {
                    "blocked": False,
                    "block_reason": None,
                    "updated_tool_args": None,
                    "messages": [],
                    "permission_override": None,
                }

        with patch.object(module, "client", client), patch.object(module, "print_status"), patch.object(
            module, "print_assistant_reply"
        ), patch.object(module, "append_session_log"), patch.object(
            tools, "run_tool_call"
        ) as run_tool, patch.object(
            module, "maybe_compact_history", side_effect=lambda conversation, state, log_path=None: conversation
        ), patch.object(module, "micro_compact", side_effect=lambda conversation: conversation):
            result = module.agent_loop(
                conversation,
                render_final=False,
                log_path="logs/test.jsonl",
                perms=FakePerms(),
                hooks=FakeHooks(),
            )

        self.assertEqual(result, "done")
        self.assertEqual(checked, [("read_file", {"path": "README.md"})])
        self.assertEqual(asked, [("read_file", {"path": "README.md"})])
        run_tool.assert_not_called()
        tool_output = next(item for item in conversation if item.get("type") == "function_call_output")
        self.assertEqual(tool_output["output"], "Permission denied by user for read_file")

    def test_post_tool_hook_does_not_run_when_permission_blocks_execution(self):
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

        class FakePerms:
            def check(self, tool_name, tool_args):
                return {"behavior": "deny", "reason": "not allowed"}

            def ask_user(self, tool_name, tool_args):
                raise AssertionError("ask_user should not run")

        class FakeHooks:
            def __init__(self):
                self.post_calls = 0

            def run_hooks(self, event, context=None):
                if event == "PostToolUse":
                    self.post_calls += 1
                    return {
                        "blocked": False,
                        "block_reason": None,
                        "updated_tool_args": None,
                        "messages": ["post hook should not run"],
                        "permission_override": None,
                    }
                return {
                    "blocked": False,
                    "block_reason": None,
                    "updated_tool_args": None,
                    "messages": [],
                    "permission_override": None,
                }

        hooks = FakeHooks()

        with patch.object(module, "client", client), patch.object(module, "print_status"), patch.object(
            module, "print_assistant_reply"
        ), patch.object(module, "append_session_log"), patch.object(
            module, "maybe_compact_history", side_effect=lambda conversation, state, log_path=None: conversation
        ), patch.object(module, "micro_compact", side_effect=lambda conversation: conversation):
            result = module.agent_loop(
                conversation,
                render_final=False,
                log_path="logs/test.jsonl",
                perms=FakePerms(),
                hooks=hooks,
            )

        self.assertEqual(result, "done")
        self.assertEqual(hooks.post_calls, 0)
        self.assertFalse(any("post hook should not run" in item.get("content", "") for item in conversation if isinstance(item, dict)))

    def test_post_tool_hook_injects_message_into_next_turn(self):
        conversation = [{"role": "user", "content": "Read docs"}]
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

        class FakeHooks:
            def run_hooks(self, event, context=None):
                if event == "PostToolUse":
                    return {
                        "blocked": False,
                        "block_reason": None,
                        "updated_tool_args": None,
                        "messages": ["Remember to summarize what you just read."],
                        "permission_override": None,
                    }
                return {
                    "blocked": False,
                    "block_reason": None,
                    "updated_tool_args": None,
                    "messages": [],
                    "permission_override": None,
                }

        with patch.object(module, "client", client), patch.object(module, "print_status"), patch.object(
            module, "print_assistant_reply"
        ), patch.object(module, "append_session_log"), patch.object(
            tools, "run_tool_call", return_value="README content"
        ), patch.object(
            module, "maybe_compact_history", side_effect=lambda conversation, state, log_path=None: conversation
        ), patch.object(module, "micro_compact", side_effect=lambda conversation: conversation):
            result = module.agent_loop(
                conversation,
                render_final=False,
                log_path="logs/test.jsonl",
                hooks=FakeHooks(),
            )

        self.assertEqual(result, "done")
        second_input = client.responses.calls[1]["input"]
        injected = [item for item in second_input if item.get("role") == "user" and "Hook note" in item.get("content", "")]
        self.assertEqual(len(injected), 1)
        self.assertIn("Remember to summarize what you just read.", injected[0]["content"])


if __name__ == "__main__":
    unittest.main()
