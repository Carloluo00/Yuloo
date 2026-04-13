# Yuloo

[中文说明](README.zh-CN.md)

Yuloo is a compact educational code-agent project inspired by
[shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code).
It rebuilds the core ideas step by step on top of Qwen models through
DashScope's OpenAI-compatible API, with a focus on making the agent loop,
tool usage, planning, delegation, permissions, and structured logging easy to inspect.

## Description

This repository is designed as a learning path rather than a single monolithic
app. Each stage introduces one new capability and keeps the code readable:

- `s01`: a minimal responses loop
- `s02`: local tool use for shell and file operations
- `s03`: todo-based planning and progress tracking
- `s04`: parent/subagent delegation with a `task` tool
- `s05`: skill discovery and on-demand `load_skill`
- `s06`: context compaction with persisted oversized tool output and transcript summaries
- `s07`: permission-aware tool execution with session-scoped approval state

The current CLI entrypoint in `main.py` uses the `s07` flow. The latest version
adds centralized runtime configuration, skill loading, context compaction,
permission-aware tool execution, preview-oriented terminal rendering, and
regression tests that protect the newer behavior.

## Highlights

- Small, readable Python codebase for studying agent architecture
- Shared `config.py` for models, client setup, prompt builders, and runtime limits
- Tool registry with `bash`, `read_file`, `write_file`, `edit_file`, `todo`, `load_skill`, and `task`
- Todo reminders that nudge the agent to keep task state updated
- Subagents that inherit parent conversation context and share filesystem access
- Skills that can be discovered from the prompt and loaded on demand
- Large tool output persisted to disk with compact previews kept in context
- Session-scoped permission state so repeated approvals can persist across one CLI run
- Terminal output trimmed to short previews while full details stay in logs
- JSONL session logs for both parent-agent activity and delegated subagent traces
- Safety checks for dangerous shell commands and workspace path escapes
- Lightweight regression tests for config, todo flow, subagent logging, compaction, terminal rendering, and permission flow

## Project Structure

- `main.py`: CLI entrypoint wired to the latest agent stage
- `config.py`: central runtime configuration and prompt/client builders
- `permission.py`: permission rules, bash validation, and approval prompts
- `s01_agent_loop.py`: minimal bash-driven agent loop
- `s02_tool_use.py`: adds file and shell tools
- `s03_todo_write.py`: adds todo planning and reminder injection
- `s04_subagents.py`: adds parent/subagent delegation
- `s05_skill_loading.py`: adds skill discovery and `load_skill`
- `s06_compact.py`: adds tool-output persistence and context compaction
- `s07_permission.py`: adds permission checks before tool execution
- `tools.py`: shared tool schema, handlers, and subagent runtime
- `terminal.py`: terminal rendering helpers
- `log.py`: JSONL session logging helpers
- `utils.py`: safe workspace path handling
- `tests/test_main.py`: CLI runtime wiring regression tests
- `tests/test_permission.py`: permission-policy regression tests
- `tests/test_tools.py`: shared tool and todo rendering regression tests
- `tests/test_s03_todo_write.py`: todo flow regression tests
- `tests/test_s04_subagent_logging.py`: subagent logging regression tests
- `tests/test_s06_compact.py`: compaction regression tests
- `tests/test_s07_permission.py`: permission-runtime regression tests
- `tests/test_terminal.py`: terminal history and preview regression tests
- `tests/test_config.py`: shared-config regression tests

## Current Runtime Model

`main.py` currently launches the `s07` agent loop, which can:

1. read a user request
2. call local tools directly
3. manage todos for multi-step work
4. delegate bounded subtasks to subagents
5. discover and load local skills
6. persist oversized tool output and compact long conversations
7. gate tool execution behind permission checks
8. reuse one permission state object across the whole CLI session
9. log both parent and subagent execution traces

Subagents inherit the parent conversation snapshot, then receive the delegated
task prompt as a new user message. They still operate in the same workspace and
can use the same local tool set, which keeps delegation inspectable while
giving workers the context they need.

## Built-in Tools

| Tool | Purpose |
| --- | --- |
| `bash` | Run shell commands inside the workspace |
| `read_file` | Read file contents with optional line limiting |
| `write_file` | Write a file |
| `edit_file` | Replace exact text in a file |
| `todo` | Track short task lists with status |
| `load_skill` | Load a named `SKILL.md` into the current context |
| `task` | Spawn a subagent for delegated work |

## Logging

Session logs are written as JSONL files under `logs/`. The current runtime logs:

- session start and end events
- assistant response blocks
- tool results and tool errors
- todo updates and reminder injections
- skill load events
- permission decisions
- subagent start, per-turn responses, tool results, and finish summaries
- context compaction events when the transcript is summarized

This makes it practical to inspect not only what the top-level agent decided,
but also what delegated workers actually did. The terminal now prints previews;
the logs retain the full detail.

## Safety Notes

- Dangerous shell patterns such as `rm -rf /`, `sudo`, `shutdown`, and `reboot`
  are blocked before execution.
- File operations pass through `safe_path()` to prevent escaping the workspace.
- Shell commands time out after the configured limit.
- Long tool output is persisted to `.task_outputs/tool-results/` and replaced
  with a compact preview in the conversation.
- Full transcript snapshots are written to `.transcripts/` when history is compacted.
- Permission checks can deny or prompt before write-like or suspicious tool calls run.

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
- `/skills`: show available skills
- `/clear`: clear the current conversation context
- `/history`: show conversation history, including assistant replies and tool records
- `q`, `quit`, `exit`: leave the program

## Validation

Current validation commands:

```bash
python -m unittest discover -s tests -p "test_*.py"
python -m py_compile config.py conftest.py log.py main.py permission.py s01_agent_loop.py s02_tool_use.py s03_todo_write.py s04_subagents.py s05_skill_loading.py s06_compact.py s07_permission.py terminal.py tools.py utils.py tests/test_config.py tests/test_main.py tests/test_permission.py tests/test_pytest_cache_policy.py tests/test_s03_todo_write.py tests/test_s04_subagent_logging.py tests/test_s06_compact.py tests/test_s07_permission.py tests/test_terminal.py tests/test_tools.py
```

## Roadmap

- Keep extending the staged learning path beyond `s07`
- Improve permission heuristics, compaction heuristics, and richer delegation coordination
- Expand test coverage for earlier tutorial stages
- Add more documentation around prompt design and runtime traces

## References

- Original project: [shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code)
- DashScope docs: <https://help.aliyun.com/zh/dashscope/>
- DashScope OpenAI compatibility docs:
  <https://help.aliyun.com/zh/dashscope/developer-reference/compatibility-of-openai-with-dashscope>
