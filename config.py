import os
from pathlib import Path

from openai import OpenAI


PROJECT_ROOT = Path(__file__).resolve().parent
WORKSPACE_DIRNAME = "YULOO_WORKSPACE"
WORKDIR = PROJECT_ROOT / WORKSPACE_DIRNAME
WORKDIR.mkdir(parents=True, exist_ok=True)
TRUST_MARKER = WORKDIR / ".YULOO" / ".YULOO_trusted"
SKILLS_DIR = PROJECT_ROOT / "skills"
LOG_DIR = PROJECT_ROOT / "logs"

API_KEY_ENV = "DASHSCOPE_API_KEY"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

DEFAULT_MODEL = "qwen3.5-flash"

TODO_REMINDER_INTERVAL = 3
TODO_REMINDER_MESSAGE = "Reminder: update your todo list if task status changed."

SUBAGENT_MAX_TURNS = 30
SHELL_TIMEOUT_SECONDS = 120
KEEP_RECENT_TOOL_RESULTS = 10
TOOL_OUTPUT_CHAR_LIMIT = 50000
PERSIST_THRESHOLD = 30000
PREVIEW_CHARS = 2000
TRANSCRIPT_DIR = WORKDIR / ".transcripts"
TOOL_RESULTS_DIR = WORKDIR / ".task_outputs" / "tool-results"
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


def build_s06_system(workdir: Path = WORKDIR) -> str:
    return (
        f"You are a coding agent at {workdir}. "
        "Use load_skill when a task needs specialized instructions before you act. "
        "Keep long-running conversations compact by persisting oversized tool output, "
        "compacting stale tool results, and summarizing history before the context window fills up."
    )


def build_s07_system(workdir: Path = WORKDIR) -> str:
    return (
        f"You are a coding agent at {workdir}. "
        "Use load_skill when a task needs specialized instructions before you act. "
        "Keep long-running conversations compact by persisting oversized tool output, "
        "compacting stale tool results, and summarizing history before the context window fills up. "
        "Some tool calls require permission; if a tool is denied, adapt and continue with the allowed path."
    )


def build_s08_system(workdir: Path = WORKDIR) -> str:
    return (
        f"{build_s07_system(workdir)} "
        "Declarative hooks may observe, block, or add context around tool calls."
    )
