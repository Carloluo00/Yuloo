import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

import s06_compact
import tools


class CompactHelpersTests(unittest.TestCase):
    def setUp(self):
        self.tmp_root = Path("tests") / "_tmp_s06_compact"
        shutil.rmtree(self.tmp_root, ignore_errors=True)
        self.tmp_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def test_s06_compact_reuses_shared_helpers_from_tools(self):
        self.assertIs(s06_compact.CompactState, tools.CompactState)
        self.assertIs(s06_compact.persist_large_output, tools.persist_large_output)
        self.assertIs(s06_compact.micro_compact, tools.micro_compact)
        self.assertIs(s06_compact.compact_history, tools.compact_history)

    def test_persist_large_output_returns_small_output_unchanged(self):
        self.assertEqual(
            s06_compact.persist_large_output("tool-1", "short output"),
            "short output",
        )

    def test_persist_large_output_writes_large_output_and_returns_preview(self):
        tmp_path = self.tmp_root / "persist"
        outputs_dir = tmp_path / ".task_outputs" / "tool-results"
        large_output = "abcdefghijklmnopqrstuvwxyz"

        with patch.object(tools, "WORKDIR", tmp_path), patch.object(
            tools, "TOOL_RESULTS_DIR", outputs_dir
        ), patch.object(tools, "PERSIST_THRESHOLD", 10), patch.object(
            tools, "PREVIEW_CHARS", 5
        ):
            persisted = s06_compact.persist_large_output("call-1", large_output)

        stored_path = outputs_dir / "call-1.txt"
        self.assertTrue(stored_path.exists())
        self.assertEqual(stored_path.read_text(), large_output)
        self.assertIn(".task_outputs", persisted)
        self.assertIn("abcde", persisted)
        self.assertIn("tool-results", persisted)

    def test_micro_compact_replaces_only_older_large_tool_results(self):
        conversation = [
            {"role": "user", "content": "inspect repo"},
            {"type": "function_call_output", "call_id": "1", "output": "a" * 130},
            {"type": "function_call_output", "call_id": "2", "output": "b" * 130},
            {"type": "function_call_output", "call_id": "3", "output": "c" * 80},
            {"type": "function_call_output", "call_id": "4", "output": "d" * 130},
        ]

        with patch.object(tools, "KEEP_RECENT_TOOL_RESULTS", 2):
            compacted = s06_compact.micro_compact(conversation)

        self.assertEqual(
            compacted[1]["output"],
            "[Earlier tool result compacted. Re-run the tool if you need full detail.]",
        )
        self.assertEqual(
            compacted[2]["output"],
            "[Earlier tool result compacted. Re-run the tool if you need full detail.]",
        )
        self.assertEqual(compacted[3]["output"], "c" * 80)
        self.assertEqual(compacted[4]["output"], "d" * 130)

    def test_compact_history_writes_transcript_and_updates_state(self):
        tmp_path = self.tmp_root / "history"
        state = s06_compact.CompactState(recent_files=["s06_compact.py", "tools.py"])
        conversation = [
            {"role": "user", "content": "do the task"},
            {"type": "function_call_output", "call_id": "1", "output": "done"},
        ]

        with patch.object(tools, "TRANSCRIPT_DIR", tmp_path / ".transcripts"), patch.object(
            tools, "summarize_history", return_value="Summary body"
        ), patch.object(tools, "print_status"):
            compacted = s06_compact.compact_history(
                conversation,
                state,
                focus="finish the implementation",
            )

        transcript_files = list((tmp_path / ".transcripts").glob("transcript_*.jsonl"))
        self.assertEqual(len(transcript_files), 1)
        transcript_text = transcript_files[0].read_text()
        self.assertIn("do the task", transcript_text)
        self.assertIn("done", transcript_text)
        self.assertTrue(state.has_compacted)
        self.assertIn("Summary body", state.last_summary)
        self.assertIn("finish the implementation", state.last_summary)
        self.assertIn("s06_compact.py", state.last_summary)
        self.assertEqual(len(compacted), 1)
        self.assertEqual(compacted[0]["role"], "user")
        self.assertIn("This conversation was compacted", compacted[0]["content"])


if __name__ == "__main__":
    unittest.main()
