import os


def color(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m"


def print_status(message: str, code: str = "90"):
    print(f"{color('[status]', code)} {message}")


def print_assistant_reply(reply: str):
    text = (reply or "").strip()
    if not text:
        return

    print(color("assistant", "32"))
    for line in text.splitlines():
        print(f"  {line}")


def print_todo_state(todo_text: str):
    text = (todo_text or "").strip()
    if not text:
        return

    print(color("todo", "35"))
    for line in text.splitlines():
        print(f"  {line}")


def print_skill_state(name: str, description: str | None = None, path: str | None = None):
    print(color("skill loaded", "34"))
    print(f"  name: {name}")
    if description:
        print(f"  desc: {description}")
    if path:
        print(f"  path: {path}")


def print_skills(skills_text: str):
    text = (skills_text or "").strip()
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
    print("  /history show recent user messages")
    print("  exit     quit the program")
    if skills_available is not None:
        print(f"  skills:  {skills_available} available")
    print(f"  log file {log_path}")


def print_history(conversation: list):
    user_messages = []
    for item in conversation:
        if isinstance(item, dict) and item.get("role") == "user":
            content = item.get("content")
            if isinstance(content, str) and content.strip():
                user_messages.append(content.strip())

    if not user_messages:
        print_status("No user messages in history yet.", "33")
        return

    print(color("recent history", "36"))
    start = max(len(user_messages) - 5, 0)
    for index, message in enumerate(user_messages[start:], start + 1):
        print(f"  {index}. {message}")


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")
