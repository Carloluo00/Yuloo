import unittest
from unittest.mock import patch

import s01


class FakeFunctionCall:
    type = "function_call"

    def __init__(self, command="dir", call_id="call_1"):
        self.arguments = f'{{"command": "{command}"}}'
        self.call_id = call_id

    def to_dict(self):
        return {
            "type": "function_call",
            "call_id": self.call_id,
            "arguments": self.arguments,
            "name": "bash",
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
    def __init__(self, response_id, output, output_text, status="completed", error=None):
        self.id = response_id
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
            return FakeResponse("resp_1", [FakeFunctionCall()], "")
        return FakeResponse("resp_2", [FakeMessage("目录里有 s01.py")], "目录里有 s01.py")


class FakeClient:
    def __init__(self):
        self.responses = FakeResponsesAPI()


class AgentLoopTests(unittest.TestCase):
    def test_tool_follow_up_uses_previous_response_id(self):
        fake_client = FakeClient()
        s01.history = [{"role": "user", "content": "查看一下文件夹有什么文件"}]

        with patch.object(s01, "client", fake_client), patch.object(
            s01, "run_bash", return_value="dir output"
        ):
            reply = s01.agent_loop(s01.history)

        self.assertEqual("目录里有 s01.py", reply)
        self.assertEqual(2, len(fake_client.responses.calls))

        second_call = fake_client.responses.calls[1]
        self.assertEqual("resp_1", second_call["previous_response_id"])
        self.assertEqual(
            [{"type": "function_call_output", "call_id": "call_1", "output": "dir output"}],
            second_call["input"],
        )


if __name__ == "__main__":
    unittest.main()
