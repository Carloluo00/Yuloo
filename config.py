import os
from pathlib import Path

from openai import OpenAI


WORKDIR = Path.cwd()
LOG_DIR = WORKDIR / "logs"

API_KEY_ENV = "DASHSCOPE_API_KEY"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

DEFAULT_MODEL = "qwen3.5-plus"
S01_MODEL = DEFAULT_MODEL
S02_MODEL = DEFAULT_MODEL
S03_MODEL = DEFAULT_MODEL
S04_MODEL = DEFAULT_MODEL
SUBAGENT_MODEL = DEFAULT_MODEL

TODO_REMINDER_INTERVAL = 3
TODO_REMINDER_MESSAGE = "Reminder: update your todo list if task status changed."

SUBAGENT_MAX_TURNS = 30
SHELL_TIMEOUT_SECONDS = 120
TOOL_OUTPUT_CHAR_LIMIT = 50000
DANGEROUS_SHELL_PATTERNS = ("rm -rf /", "sudo", "shutdown", "reboot", "> /dev/")
TODO_TOOL_FORMAT_GUIDANCE = (
    "Use the todo tool with items as a native JSON array. "
    'Do not wrap todo.items in quotes or stringify the array. '
    'Correct: {"items":[{"id":"1","text":"Inspect logs","status":"in_progress"}]}.'
)


def build_client() -> OpenAI:
    return OpenAI(
        api_key=os.getenv(API_KEY_ENV),
        base_url=BASE_URL,
    )


def build_s01_system(workdir: Path = WORKDIR) -> str:
    return f"You are a coding agent at {workdir}. Use bash to solve tasks. Act, don't explain."


def build_s02_system(workdir: Path = WORKDIR) -> str:
    return f"You are a coding agent at {workdir}.  Use tools to solve tasks. Act, don't explain."


def build_s03_system(workdir: Path = WORKDIR) -> str:
    return (
        f"You are a coding agent at {workdir}. "
        "Always plan first. Use the todo tool to plan multi-step tasks. "
        "Mark a task in_progress before starting it and completed when done. "
        f"{TODO_TOOL_FORMAT_GUIDANCE}"
    )


def build_s04_system(workdir: Path = WORKDIR) -> str:
    return (
        f"You are a coding agent at {workdir}. "
        "Use the task tool to delegate exploration or subtasks. "
        f"{TODO_TOOL_FORMAT_GUIDANCE}"
    )


def build_subagent_system(workdir: Path = WORKDIR) -> str:
    return (
        f"You are a coding subagent at {workdir}. "
        "Complete the given task, then summarize your findings. "
        f"{TODO_TOOL_FORMAT_GUIDANCE}"
    )
