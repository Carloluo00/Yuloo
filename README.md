# Yuloo

[中文说明](README.zh-CN.md)

Yuloo is a small learning project inspired by
[shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code),
adapted to run on Qwen models through DashScope's OpenAI-compatible API.

## What It Does

The repository follows a step-by-step agent-building path:

- `s01_agent_loop.py`: minimal agent loop
- `s02_tool_use.py`: tool calling for shell and file operations
- `s03_todo_write.py`: todo-driven planning and progress tracking

The current CLI entrypoint in [main.py](/e:/Project/TEst1/main.py) uses the
`s03` flow.

## Current Status

Implemented so far:

- `s01`: basic loop
- `s02`: tool use
- `s03`: explicit planning with a `todo` tool

Current `s03` behavior includes:

- a dedicated `todo` tool in [tools.py](/e:/Project/TEst1/tools.py)
- explicit planning instructions before multi-step work
- reminder injection when todos have not been updated for several tool rounds
- todo-specific terminal rendering in [terminal.py](/e:/Project/TEst1/terminal.py)
- structured JSONL session logging in [log.py](/e:/Project/TEst1/log.py)

## Project Structure

- [main.py](/e:/Project/TEst1/main.py): CLI entrypoint
- [s01_agent_loop.py](/e:/Project/TEst1/s01_agent_loop.py): baseline loop
- [s02_tool_use.py](/e:/Project/TEst1/s02_tool_use.py): tool use stage
- [s03_todo_write.py](/e:/Project/TEst1/s03_todo_write.py): todo planning stage
- [tools.py](/e:/Project/TEst1/tools.py): tool registry and handlers
- [terminal.py](/e:/Project/TEst1/terminal.py): terminal output helpers
- [log.py](/e:/Project/TEst1/log.py): session logging
- [utils.py](/e:/Project/TEst1/utils.py): workspace path safety
- [tests/test_s03_todo_write.py](/e:/Project/TEst1/tests/test_s03_todo_write.py): regression tests for the todo flow

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
- Large tool output is truncated before being returned to the model.

## Run Locally

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
- Explore background jobs, delegation, and multi-agent workflows in later steps

## References

- Original project: [shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code)
- DashScope docs: <https://help.aliyun.com/zh/dashscope/>
- DashScope OpenAI compatibility docs:
  <https://help.aliyun.com/zh/dashscope/developer-reference/compatibility-of-openai-with-dashscope>
