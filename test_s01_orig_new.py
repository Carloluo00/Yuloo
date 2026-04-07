import io
import json
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import s01_orig_new
import s01_agent_loop
import s01_logging
import cli


class FakeFunctionCall:
    type = "function_call"

    def __init__(self, command="dir", call_id="call_1"):
        self.arguments = f'{{"command": "{command}"}}'
        self.call_id = call_id
        self.name = "bash"
        self.id = "msg_1"
        self.namespace = None
        self.status = "completed"

    def to_dict(self):
        return {
            "type": "function_call",
            "call_id": self.call_id,
            "arguments": self.arguments,
            "name": self.name,
            "id": self.id,
            "namespace": self.namespace,
            "status": self.status,
        }


class FakeMessage:
    type = "message"

    def __init__(self, text):
        self.text = text

    def to_dict(self):
        return {
            "role": "assistant",
            "type": "message",
            "content": self.text,
        }


class FakeResponse:
    def __init__(self, output, output_text, status="completed", error=None):
        self.output = output
        self.output_text = output_text
        self.status = status
        self.error = error


class FakeResponsesAPI:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            return FakeResponse([FakeFunctionCall("dir")], "")
        return FakeResponse([FakeMessage("目录里有 s01_orig_new.py")], "目录里有 s01_orig_new.py")


class FakeClient:
    def __init__(self):
        self.responses = FakeResponsesAPI()


class AgentLoopTests(unittest.TestCase):
    def test_agent_loop_reports_tool_activity_and_reply(self):
        fake_client = FakeClient()
        output = io.StringIO()

        with patch.object(s01_agent_loop, "client", fake_client), patch.object(
            s01_agent_loop, "run_bash", return_value="dir output"
        ), redirect_stdout(output):
            reply = s01_agent_loop.agent_loop([{"role": "user", "content": "看看目录"}])

        printed = output.getvalue()
        self.assertEqual("目录里有 s01_orig_new.py", reply)
        self.assertIn("thinking", printed.lower())
        self.assertIn("running bash", printed.lower())
        self.assertIn("目录里有 s01_orig_new.py", printed)

    def test_agent_loop_logs_full_event_dicts(self):
        fake_client = FakeClient()

        with patch.object(s01_agent_loop, "client", fake_client), patch.object(
            s01_agent_loop, "run_bash", return_value="dir output"
        ), patch.object(s01_agent_loop, "append_session_log") as log_mock:
            s01_agent_loop.agent_loop(
                [{"role": "user", "content": "看看目录"}],
                render_final=False,
                log_path="logs/session-test.jsonl",
            )

        assistant_payloads = [
            call.args[1] for call in log_mock.call_args_list if call.args[0] == "assistant_response"
        ]
        tool_payloads = [
            call.args[1] for call in log_mock.call_args_list if call.args[0] == "tool_result"
        ]
        assistant_payload = next(payload for payload in assistant_payloads if payload["type"] == "function_call")
        tool_payload = tool_payloads[0]
        self.assertEqual("function_call", assistant_payload["type"])
        self.assertEqual("bash", assistant_payload["name"])
        self.assertEqual('{"command": "dir"}', assistant_payload["arguments"])
        self.assertEqual("function_call_output", tool_payload["type"])
        self.assertEqual("call_1", tool_payload["call_id"])
        self.assertEqual("dir output", tool_payload["output"])


class CliTests(unittest.TestCase):
    def test_empty_input_prompts_retry_instead_of_exit(self):
        output = io.StringIO()

        with patch.object(
            cli, "agent_loop", side_effect=["已处理"]
        ) as agent_loop_mock, patch.object(
            cli, "create_session_log_file", return_value="logs/session-123.jsonl"
        ), patch.object(
            cli, "append_session_log"
        ), patch(
            "builtins.input", side_effect=["", "hello", "exit"]
        ), redirect_stdout(output):
            cli.run_cli()

        printed = output.getvalue()
        self.assertEqual(1, agent_loop_mock.call_count)
        self.assertIn("请输入内容", printed)
        self.assertIn("已处理", printed)

    def test_clear_command_resets_conversation(self):
        conversation = [{"role": "user", "content": "old"}]
        output = io.StringIO()

        with patch.object(cli, "append_session_log"), redirect_stdout(output):
            handled = cli.handle_builtin_command("/clear", conversation, "logs/session-test.jsonl")

        self.assertTrue(handled)
        self.assertEqual([], conversation)
        self.assertIn("已清空", output.getvalue())

    def test_run_cli_creates_session_log_and_logs_user_input(self):
        output = io.StringIO()

        with patch.object(
            cli, "agent_loop", side_effect=["已处理"]
        ), patch.object(
            cli, "create_session_log_file", return_value="logs/session-123.jsonl"
        ), patch.object(
            cli, "append_session_log"
        ) as log_mock, patch(
            "builtins.input", side_effect=["hello", "exit"]
        ), redirect_stdout(output):
            cli.run_cli()

        events = [call.args[0] for call in log_mock.call_args_list]
        self.assertIn("session_started", events)
        self.assertIn("user_input", events)
        self.assertIn("session_ended", events)


class LoggingTests(unittest.TestCase):
    def test_create_session_log_file_creates_new_log(self):
        log_dir = os.path.join(os.getcwd(), "test_artifacts")
        log_path = s01_logging.create_session_log_file(log_dir=log_dir)

        self.assertTrue(os.path.exists(log_path))
        self.assertIn("s01_session_", os.path.basename(log_path))

        with open(log_path, "r", encoding="utf-8") as handle:
            payload = json.loads(handle.readline())

        self.assertEqual("session_started", payload["event"])
        self.assertIn("session_id", payload["payload"])
        os.remove(log_path)

    def test_append_session_log_writes_incremental_event_payload(self):
        log_dir = os.path.join(os.getcwd(), "test_artifacts")
        log_path = os.path.join(log_dir, "session-log.jsonl")
        if os.path.exists(log_path):
            os.remove(log_path)

        s01_logging.append_session_log(
            "user_input",
            {"content": "hello"},
            log_path=log_path,
        )

        with open(log_path, "r", encoding="utf-8") as handle:
            payload = json.loads(handle.readline())

        self.assertEqual("user_input", payload["event"])
        self.assertEqual({"content": "hello"}, payload["payload"])
        self.assertNotIn("conversation", payload)
        os.remove(log_path)


class EntrypointTests(unittest.TestCase):
    def test_entrypoint_reexports_run_cli(self):
        self.assertTrue(callable(s01_orig_new.run_cli))


if __name__ == "__main__":
    unittest.main()
