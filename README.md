# Yuloo

[中文说明](README.zh-CN.md)

Yuloo is a compact, step-by-step agent engineering project built on top of
DashScope's OpenAI-compatible API. The repository starts from a minimal single
agent loop and incrementally adds tool calling, todo-based planning,
subagent delegation, structured JSONL logging, and a shared runtime
configuration layer.

## Description

This repository is designed as a learning path rather than a single monolithic
application. Each `s0x_*.py` file captures one stage in the agent's evolution:

- `s01_agent_loop.py`: minimal agent loop with a single `bash` tool
- `s02_tool_use.py`: generalized tool calling for shell and file operations
- `s03_todo_write.py`: explicit todo planning and progress tracking
- `s04_subagents.py`: parent-agent delegation through a `task` tool and
  subagent execution tracing

The current CLI entrypoint in [main.py](main.py) uses the `s04` flow.

## Current Capabilities

- DashScope-backed agent runtime through the OpenAI-compatible SDK
- Tool calling for shell, file read, file write, and targeted file edit
- Todo management with `pending`, `in_progress`, and `completed` states
- Parent-agent delegation to filesystem-sharing subagents through `task`
- Structured JSONL session logs for both the parent agent and subagent traces
- Centralized runtime settings in [config.py](config.py)
- Regression tests for todo flow, shared config wiring, and subagent logging

## Repository Structure

- [main.py](main.py): interactive CLI entrypoint
- [config.py](config.py): shared runtime configuration, prompt builders, and
  client factory
- [s01_agent_loop.py](s01_agent_loop.py): baseline single-tool agent loop
- [s02_tool_use.py](s02_tool_use.py): general tool-use stage
- [s03_todo_write.py](s03_todo_write.py): todo-driven planning stage
- [s04_subagents.py](s04_subagents.py): delegated parent-agent stage
- [tools.py](tools.py): tool registry, handlers, and subagent runtime
- [terminal.py](terminal.py): terminal rendering helpers
- [log.py](log.py): JSONL session logging utilities
- [utils.py](utils.py): workspace-safe path validation
- [tests/test_s03_todo_write.py](tests/test_s03_todo_write.py): todo flow tests
- [tests/test_s04_subagent_logging.py](tests/test_s04_subagent_logging.py):
  subagent logging tests
- [tests/test_config.py](tests/test_config.py): shared configuration tests

## Built-in Tools

| Tool | Purpose |
| --- | --- |
| `bash` | Run shell commands inside the workspace |
| `read_file` | Read file contents with optional line limits |
| `write_file` | Write full file contents |
| `edit_file` | Replace exact text in a file |
| `todo` | Track short task lists for multi-step work |
| `task` | Spawn a fresh-context subagent from the parent agent |

## Logging

Session logs are written to `logs/*.jsonl`. Logged events include:

- session start and end markers
- user input
- assistant response blocks
- tool results and tool errors
- todo reminder injection
- subagent lifecycle events:
  `subagent_started`, `subagent_response`, `subagent_tool_result`,
  `subagent_finished`

This makes it possible to reconstruct both the parent agent's execution flow
and the delegated subagent trace from a single session log.

## Safety Notes

- Dangerous shell commands such as `rm -rf /`, `sudo`, `shutdown`, and
  `reboot` are blocked.
- File operations go through `safe_path()` in [utils.py](utils.py) to prevent
  escaping the workspace.
- Shell commands are time-limited.
- Large tool outputs are truncated before returning them to the model.

## Configuration

[config.py](config.py) is the single source of truth for:

- model selection for each tutorial stage
- DashScope base URL and API key environment variable name
- working directory and log directory defaults
- todo reminder behavior
- subagent turn limits
- shell timeout and output truncation limits
- system prompt builders for each stage

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

- `/help`: show available commands
- `/clear`: clear the current conversation context
- `/history`: show recent user messages
- `q`, `quit`, `exit`: leave the program

## Validation

Current validation commands:

- `python -m unittest discover -s tests -p "test_*.py"`
- `python -m py_compile config.py log.py utils.py s01_agent_loop.py s02_tool_use.py s03_todo_write.py s04_subagents.py tools.py main.py`

## Roadmap

- continue the staged learning path beyond `s04`
- add richer agent coordination patterns and execution controls
- expand test coverage for earlier tutorial stages
- improve documentation around log analysis and model configuration

## References

- Original project inspiration:
  [shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code)
- DashScope docs: <https://help.aliyun.com/zh/dashscope/>
- DashScope OpenAI compatibility docs:
  <https://help.aliyun.com/zh/dashscope/developer-reference/compatibility-of-openai-with-dashscope>
