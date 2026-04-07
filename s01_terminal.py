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


def print_banner(model: str, cwd: str, log_path: str):
    print(color("=" * 56, "36"))
    print(color("s01 interactive shell", "36"))
    print(f"  model: {model}")
    print(f"  cwd:   {cwd}")
    print("  commands: /help  /clear  /history  exit")
    print(f"  log:   {log_path}")
    print(color("=" * 56, "36"))


def print_help(log_path: str):
    print(color("commands", "36"))
    print("  /help    show available commands")
    print("  /clear   clear current conversation context")
    print("  /history show recent user messages")
    print("  exit     quit the program")
    print(f"  log file {log_path}")


def print_history(conversation: list):
    user_messages = []
    for item in conversation:
        if isinstance(item, dict) and item.get("role") == "user":
            content = item.get("content")
            if isinstance(content, str) and content.strip():
                user_messages.append(content.strip())

    if not user_messages:
        print_status("当前还没有可显示的历史消息。", "33")
        return

    print(color("recent history", "36"))
    start = max(len(user_messages) - 5, 0)
    for index, message in enumerate(user_messages[start:], start + 1):
        print(f"  {index}. {message}")


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")
