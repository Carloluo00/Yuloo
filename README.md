# Yuloo

[中文说明](README.zh-CN.md)

Yuloo is a compact educational code-agent project inspired by
[shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code).
It rebuilds the core ideas step by step on top of Qwen models through
DashScope's OpenAI-compatible API, with a focus on making the agent loop,
tool usage, planning, delegation, and structured logging easy to inspect.

## Description

This repository is designed as a learning path rather than a single monolithic
app. Each stage introduces one new capability and keeps the code readable:

- `s01`: a minimal responses loop
- `s02`: local tool use for shell and file operations
- `s03`: todo-based planning and progress tracking
- `s04`: parent/subagent delegation with a `task` tool

The current CLI entrypoint in `main.py` uses the `s04` flow. The latest version
adds centralized runtime configuration, subagent lifecycle logging, and
regression tests that protect the newer delegation behavior.

## Highlights

- Small, readable Python codebase for studying agent architecture
- Shared `config.py` for models, client setup, prompt builders, and runtime limits
- Tool registry with `bash`, `read_file`, `write_file`, `edit_file`, `todo`, and `task`
- Todo reminders that nudge the agent to keep task state updated
- Subagents with isolated conversation context and shared filesystem access
- JSONL session logs for both parent-agent activity and delegated subagent traces
- Safety checks for dangerous shell commands and workspace path escapes
- Lightweight regression tests for config, todo flow, and subagent logging

## Project Structure

- `main.py`: CLI entrypoint wired to the latest agent stage
- `config.py`: central runtime configuration and prompt/client builders
- `s01_agent_loop.py`: minimal bash-driven agent loop
- `s02_tool_use.py`: adds file and shell tools
- `s03_todo_write.py`: adds todo planning and reminder injection
- `s04_subagents.py`: adds parent/subagent delegation
- `tools.py`: shared tool schema, handlers, and subagent runtime
- `terminal.py`: terminal rendering helpers
- `log.py`: JSONL session logging helpers
- `utils.py`: safe workspace path handling
- `tests/test_s03_todo_write.py`: todo flow regression tests
- `tests/test_s04_subagent_logging.py`: subagent logging regression tests
- `tests/test_config.py`: shared-config regression tests

## Current Runtime Model

`main.py` currently launches the `s04` agent loop, which can:

1. read a user request
2. call local tools directly
3. manage todos for multi-step work
4. delegate bounded subtasks to subagents
5. log both parent and subagent execution traces

Subagents do not inherit the full parent conversation. They start with a fresh
prompt, but they operate in the same workspace and can use the same local tool
set. This keeps delegation inspectable and easy to debug.

## Built-in Tools

| Tool | Purpose |
| --- | --- |
| `bash` | Run shell commands inside the workspace |
| `read_file` | Read file contents with optional line limiting |
| `write_file` | Write a file |
| `edit_file` | Replace exact text in a file |
| `todo` | Track short task lists with status |
| `task` | Spawn a subagent for delegated work |

## Logging

Session logs are written as JSONL files under `logs/`. The current runtime logs:

- session start and end events
- assistant response blocks
- tool results and tool errors
- todo updates and reminder injections
- subagent start, per-turn responses, tool results, and finish summaries

This makes it practical to inspect not only what the top-level agent decided,
but also what delegated workers actually did.

## Safety Notes

- Dangerous shell patterns such as `rm -rf /`, `sudo`, `shutdown`, and `reboot`
  are blocked before execution.
- File operations pass through `safe_path()` to prevent escaping the workspace.
- Shell commands time out after the configured limit.
- Long tool output is truncated before being returned to the model.

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

Current validation commands:

```bash
python -m unittest discover -s tests -p "test_*.py"
python -m py_compile config.py log.py main.py s01_agent_loop.py s02_tool_use.py s03_todo_write.py s04_subagents.py terminal.py tools.py utils.py tests/test_config.py tests/test_s03_todo_write.py tests/test_s04_subagent_logging.py
```

## Roadmap

- Keep extending the staged learning path beyond `s04`
- Improve delegation heuristics and richer subagent coordination
- Expand test coverage for earlier tutorial stages
- Add more documentation around prompt design and runtime traces

## References

- Original project: [shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code)
- DashScope docs: <https://help.aliyun.com/zh/dashscope/>
- DashScope OpenAI compatibility docs:
  <https://help.aliyun.com/zh/dashscope/developer-reference/compatibility-of-openai-with-dashscope>
