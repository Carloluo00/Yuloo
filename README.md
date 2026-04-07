# Qwen Claude Code Learning Project

This repository is a learning-oriented reimplementation of
[shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code),
adapted to run on Qwen models through DashScope's OpenAI-compatible API.

## What This Project Is

The project follows the original step-by-step teaching style:

- `s01_agent_loop.py`: the minimal agent loop
- `s02_tool_use.py`: tool calling for file and shell operations
- `s03_todo_write.py`: explicit planning with a todo tool and progress tracking

The current CLI entrypoint in [main.py](/e:/Project/TEst1/main.py) is wired to
the `s03` flow.

## Current Status

Completed:

- `s01`: basic agent loop
- `s02`: tool use
- `s03`: todo-driven planning and progress updates

Current `s03` improvements include:

- a dedicated `todo` tool in [tools.py](/e:/Project/TEst1/tools.py)
- explicit planning instructions before multi-step work
- reminder injection when the agent has not updated todos for several tool rounds
- todo-specific terminal output in [terminal.py](/e:/Project/TEst1/terminal.py)
- more structured session logging in [log.py](/e:/Project/TEst1/log.py)

## Project Structure

- [main.py](/e:/Project/TEst1/main.py): CLI entrypoint
- [s01_agent_loop.py](/e:/Project/TEst1/s01_agent_loop.py): baseline loop
- [s02_tool_use.py](/e:/Project/TEst1/s02_tool_use.py): tool use step
- [s03_todo_write.py](/e:/Project/TEst1/s03_todo_write.py): todo planning step
- [tools.py](/e:/Project/TEst1/tools.py): tool registry and handlers
- [terminal.py](/e:/Project/TEst1/terminal.py): terminal rendering helpers
- [log.py](/e:/Project/TEst1/log.py): JSONL session logging
- [utils.py](/e:/Project/TEst1/utils.py): workspace path safety
- [tests/test_s03_todo_write.py](/e:/Project/TEst1/tests/test_s03_todo_write.py): regression tests for the todo workflow

## Built-in Tools

| Tool | Purpose |
| --- | --- |
| `bash` | Run shell commands in the workspace |
| `read_file` | Read file contents |
| `write_file` | Write a file |
| `edit_file` | Replace exact text in a file |
| `todo` | Track a short task list with `pending`, `in_progress`, and `completed` states |

## Safety Notes

- Dangerous shell commands such as `rm -rf /`, `sudo`, `shutdown`, and `reboot`
  are blocked in [tools.py](/e:/Project/TEst1/tools.py).
- File operations go through `safe_path()` in [utils.py](/e:/Project/TEst1/utils.py)
  to prevent escaping the workspace.
- Shell commands time out after 120 seconds.
- Tool output is truncated to avoid overwhelming the context window.

## Running Locally

1. Install Python 3.8+.
2. Install dependencies:

```bash
pip install openai python-dotenv
```

3. Set your DashScope API key:

```bash
set DASHSCOPE_API_KEY=your_api_key
```

4. Start the CLI:

```bash
python main.py
```

## CLI Commands

- `/help`: show command help
- `/clear`: clear the current conversation context
- `/history`: show recent user messages
- `q`, `quit`, `exit`: leave the program

## Validation

Recent checks for the `s03` workflow:

- `python -m unittest tests.test_s03_todo_write`
- `python -m unittest discover -s tests -p "test_*.py"`
- `python -m compileall main.py s03_todo_write.py log.py terminal.py tools.py tests/test_s03_todo_write.py`

## Roadmap

- Continue implementing later lessons beyond `s03`
- Add more tools as the tutorial expands
- Explore background tasks, delegation, and team workflows in later stages

## References

- Original project: [shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code)
- DashScope docs: <https://help.aliyun.com/zh/dashscope/>
- DashScope OpenAI compatibility docs:
  <https://help.aliyun.com/zh/dashscope/developer-reference/compatibility-of-openai-with-dashscope>
