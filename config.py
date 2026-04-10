import os
from pathlib import Path

from openai import OpenAI


WORKDIR = Path.cwd()
SKILLS_DIR = WORKDIR / "skills"
LOG_DIR = WORKDIR / "logs"

API_KEY_ENV = "DASHSCOPE_API_KEY"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

DEFAULT_MODEL = "qwen3.5-plus"

TODO_REMINDER_INTERVAL = 3
TODO_REMINDER_MESSAGE = "Reminder: update your todo list if task status changed."

SUBAGENT_MAX_TURNS = 30
SHELL_TIMEOUT_SECONDS = 120
TOOL_OUTPUT_CHAR_LIMIT = 50000
DANGEROUS_SHELL_PATTERNS = ("rm -rf /", "sudo", "shutdown", "reboot", "> /dev/")


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
    )


def build_s04_system(workdir: Path = WORKDIR) -> str:
    return (
        f"You are a coding agent at {workdir}. "
        "Use the task tool to delegate exploration or subtasks. "
    )


def build_subagent_system(workdir: Path = WORKDIR) -> str:
    return (
        f"You are a coding subagent at {workdir}. "
        "Complete the given task, then summarize your findings. "
    )


def build_s05_system():
    return (
        f"You are a coding agent at {WORKDIR}. "
        "Use load_skill when a task needs specialized instructions before you act."
    )
