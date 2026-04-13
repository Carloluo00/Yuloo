import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import terminal


class TerminalHistoryTests(unittest.TestCase):
    def test_print_assistant_reply_truncates_long_output(self):
        long_reply = "A" * 80

        buffer = io.StringIO()
        with redirect_stdout(buffer), patch.object(terminal, "TERMINAL_PREVIEW_CHARS", 20):
            terminal.print_assistant_reply(long_reply)

        output = buffer.getvalue()
        self.assertIn("A" * 20, output)
        self.assertNotIn("A" * 40, output)
        self.assertIn("...", output)

    def test_print_history_includes_assistant_messages_and_plan_records(self):
        conversation = [
            {"role": "user", "content": "Please make a plan"},
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "I will inspect the repo first."}],
            },
            {
                "type": "function_call",
                "name": "todo",
                "arguments": '{"items":[{"id":"1","text":"Inspect repo","status":"in_progress"}]}',
                "call_id": "todo-1",
            },
            {
                "type": "function_call_output",
                "call_id": "todo-1",
                "output": "[>] #1: Inspect repo\n(0/1 completed)",
            },
            {"role": "user", "content": "Continue"},
            {"type": "message", "role": "assistant", "text": "Done."},
        ]

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            terminal.print_history(conversation)

        output = buffer.getvalue()
        self.assertIn("Please make a plan", output)
        self.assertIn("I will inspect the repo first.", output)
        self.assertIn("[>] #1: Inspect repo", output)
        self.assertIn("Continue", output)
        self.assertIn("Done.", output)

    def test_print_history_truncates_each_entry_preview(self):
        conversation = [
            {"role": "user", "content": "B" * 70},
            {"type": "message", "role": "assistant", "text": "C" * 70},
        ]

        buffer = io.StringIO()
        with redirect_stdout(buffer), patch.object(terminal, "TERMINAL_PREVIEW_CHARS", 20):
            terminal.print_history(conversation)

        output = buffer.getvalue()
        self.assertIn("B" * 20, output)
        self.assertIn("C" * 20, output)
        self.assertNotIn("B" * 40, output)
        self.assertNotIn("C" * 40, output)
        self.assertIn("...", output)


if __name__ == "__main__":
    unittest.main()
