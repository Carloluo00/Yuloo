import os
from pathlib import Path

from config import WORKDIR
from log import append_session_log
from terminal import clear_screen, print_banner, print_help, print_history, print_skills, print_status


EXIT_COMMANDS = {"q", "quit", "exit"}
BUILTIN_COMMANDS = {"/help", "/skills", "/clear", "/history"}


def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


def count_available_skills(skills_text: str) -> int:
    lines = [line.strip() for line in skills_text.splitlines() if line.strip()]
    return 0 if lines == ["(no skills available)"] else len(lines)


def is_exit_command(query: str) -> bool:
    return query.strip().lower() in EXIT_COMMANDS


def handle_builtin_command(
    query: str,
    conversation: list,
    log_path: str,
    *,
    model: str,
    runtime_name: str,
    available_skills_text: str,
    cwd: str | None = None,
) -> bool:
    command = query.strip().lower()
    if command not in BUILTIN_COMMANDS:
        return False

    skill_count = count_available_skills(available_skills_text)
    current_cwd = cwd or os.getcwd()
    if command == "/help":
        print_help(log_path, skill_count)
    elif command == "/skills":
        print_skills(available_skills_text)
        append_session_log("skills_viewed", {"skills_available": skill_count}, log_path)
    elif command == "/clear":
        conversation.clear()
        append_session_log("conversation_cleared", {"remaining_messages": len(conversation)}, log_path)
        clear_screen()
        print_banner(
            model,
            current_cwd,
            log_path,
            runtime_name=runtime_name,
            skills_available=skill_count,
        )
        print_status("Conversation context cleared.", "33")
    elif command == "/history":
        print_history(conversation)
    return True


def extract_response_text(response) -> str:
    output_text = getattr(response, "output_text", "")
    if output_text:
        return output_text

    # Different SDK objects expose text in different shapes; fall back from direct text to content items.
    parts = []
    for block in getattr(response, "output", []):
        if hasattr(block, "text"):
            parts.append(block.text)
            continue
        content = getattr(block, "content", None)
        if not isinstance(content, list):
            continue
        for item in content:
            text = getattr(item, "text", "")
            if text:
                parts.append(text)
    return "".join(parts)

def _read_text_with_fallback(path, *, return_encoding: bool = False):
    try:
        text = path.read_text(encoding="utf-8")
        encoding = "utf-8"
    except UnicodeDecodeError:
        # The tutorial targets Windows too, so tolerate legacy local encodings when reading skills/files.
        text = path.read_text(encoding="gbk", errors="replace")
        encoding = "gbk"

    if return_encoding:
        return text, encoding
    return text
