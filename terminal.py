import json
import os

TERMINAL_PREVIEW_CHARS = 280


def color(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m"


def _preview_text(text: str, limit: int | None = None) -> str:
    value = (text or "").strip()
    max_chars = TERMINAL_PREVIEW_CHARS if limit is None else limit
    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars]}..."


def print_status(message: str, code: str = "90"):
    print(f"{color('[status]', code)} {_preview_text(message)}")


def print_assistant_reply(reply: str):
    text = _preview_text(reply)
    if not text:
        return

    print(color("assistant", "32"))
    for line in text.splitlines():
        print(f"  {line}")


def print_todo_state(todo_text: str):
    text = _preview_text(todo_text)
    if not text:
        return

    print(color("todo", "35"))
    for line in text.splitlines():
        print(f"  {line}")


def print_skill_state(name: str, description: str | None = None, path: str | None = None):
    print(color("skill loaded", "34"))
    print(f"  name: {_preview_text(name)}")
    if description:
        print(f"  desc: {_preview_text(description)}")
    if path:
        print(f"  path: {_preview_text(path)}")


def print_skills(skills_text: str):
    text = _preview_text(skills_text)
    if not text:
        print_status("No skills available.", "33")
        return

    print(color("skills", "34"))
    for line in text.splitlines():
        print(f"  {line}")


def print_banner(
    model: str,
    cwd: str,
    log_path: str,
    runtime_name: str | None = None,
    skills_available: int | None = None,
):
    print(color("=" * 56, "36"))
    print(color("interactive shell", "36"))
    print(f"  model: {model}")
    if runtime_name:
        print(f"  runtime: {runtime_name}")
    if skills_available is not None:
        print(f"  skills:  {skills_available} available")
    print(f"  cwd:   {cwd}")
    print("  commands: /help  /skills  /clear  /history  exit")
    print(f"  log:   {log_path}")
    print(color("=" * 56, "36"))


def print_help(log_path: str, skills_available: int | None = None):
    print(color("commands", "36"))
    print("  /help    show available commands")
    print("  /skills  show available skills")
    print("  /clear   clear current conversation context")
    print("  /history show conversation history")
    print("  exit     quit the program")
    if skills_available is not None:
        print(f"  skills:  {skills_available} available")
    print(f"  log file {log_path}")


def _history_text(value) -> str:
    if isinstance(value, str):
        return value.strip()
    if not isinstance(value, list):
        return ""

    parts = []
    for item in value:
        if isinstance(item, dict):
            text = item.get("text", "")
        else:
            text = getattr(item, "text", "")
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())
    return "\n".join(parts)


def _history_entries(conversation: list) -> list[tuple[str, str]]:
    entries = []
    tool_names: dict[str, str] = {}

    for item in conversation:
        if not isinstance(item, dict):
            continue

        role = item.get("role")
        if role in {"user", "assistant", "system"}:
            text = _history_text(item.get("content"))
            if text:
                entries.append((role, text))
                continue

        item_type = item.get("type")
        if item_type == "message":
            text = _history_text(item.get("content")) or _history_text(item.get("text"))
            if text:
                entries.append((item.get("role", "assistant"), text))
        elif item_type == "function_call":
            tool_name = item.get("name", "tool")
            call_id = item.get("call_id")
            if isinstance(call_id, str):
                tool_names[call_id] = tool_name
            arguments = item.get("arguments", "")
            if isinstance(arguments, str) and arguments.strip():
                try:
                    arguments = json.dumps(json.loads(arguments), ensure_ascii=False)
                except json.JSONDecodeError:
                    arguments = arguments.strip()
                entries.append((f"{tool_name} call", str(arguments)))
        elif item_type == "function_call_output":
            output = item.get("output", "")
            if isinstance(output, str) and output.strip():
                tool_name = tool_names.get(item.get("call_id"), "tool")
                entries.append((f"{tool_name} result", output.strip()))

    return entries


def print_history(conversation: list):
    entries = _history_entries(conversation)
    if not entries:
        print_status("No conversation history yet.", "33")
        return

    print(color("conversation history", "36"))
    for index, (label, text) in enumerate(entries, 1):
        print(f"  {index}. [{label}]")
        for line in _preview_text(text).splitlines():
            print(f"     {line}")


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")
