import os

from s02_tool_use import MODEL, agent_loop
from log import append_session_log, create_session_log_file
from terminal import (
    clear_screen,
    print_assistant_reply,
    print_banner,
    print_help,
    print_history,
    print_status,
)


PROMPT = "\033[36ms01 >> \033[0m"
EXIT_COMMANDS = {"q", "quit", "exit"}
BUILTIN_COMMANDS = {"/help", "/clear", "/history"}


def is_exit_command(query: str) -> bool:
    return query.strip().lower() in EXIT_COMMANDS


def handle_builtin_command(query: str, conversation: list, log_path: str) -> bool:
    command = query.strip().lower()
    if command not in BUILTIN_COMMANDS:
        return False

    if command == "/help":
        print_help(log_path)
    elif command == "/clear":
        conversation.clear()
        append_session_log(
            "conversation_cleared",
            {"remaining_messages": len(conversation)},
            log_path,
        )
        clear_screen()
        print_banner(MODEL, os.getcwd(), log_path)
        print_status("已清空当前会话上下文。", "33")
    elif command == "/history":
        print_history(conversation)
    return True


def run_cli():
    conversation = []
    log_path = create_session_log_file(model=MODEL, cwd=os.getcwd())
    if not os.path.exists(log_path) or os.path.getsize(log_path) == 0:
        session_id = os.path.splitext(os.path.basename(log_path))[0].replace("s01_session_", "")
        append_session_log(
            "session_started",
            {"session_id": session_id, "model": MODEL, "cwd": os.getcwd()},
            log_path,
        )

    print_banner(MODEL, os.getcwd(), log_path)

    while True:
        try:
            query = input(PROMPT)
        except (EOFError, KeyboardInterrupt):
            print()
            append_session_log("session_ended", {"reason": "interrupt"}, log_path)
            print_status("会话已结束。", "90")
            break

        trimmed = query.strip()
        if not trimmed:
            print_status("请输入内容，或使用 /help 查看命令。", "33")
            continue

        if is_exit_command(trimmed):
            append_session_log("session_ended", {"reason": "exit"}, log_path)
            print_status("下次见。", "90")
            break

        if handle_builtin_command(trimmed, conversation, log_path):
            continue

        conversation.append({"role": "user", "content": query})
        append_session_log("user_input", {"content": query}, log_path)
        reply = agent_loop(conversation, render_final=False, log_path=log_path)
        if reply:
            print_assistant_reply(reply)
        else:
            print_status("这次没有返回可显示的文本。", "33")
        print()

if __name__ == "__main__":
    run_cli()