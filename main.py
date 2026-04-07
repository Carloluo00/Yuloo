import os

from log import append_session_log, create_session_log_file
from s03_todo_write import MODEL, agent_loop
from terminal import (
    clear_screen,
    print_assistant_reply,
    print_banner,
    print_help,
    print_history,
    print_status,
)


PROMPT = "\033[36magent >> \033[0m"
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
        append_session_log("conversation_cleared", {"remaining_messages": len(conversation)}, log_path)
        clear_screen()
        print_banner(MODEL, os.getcwd(), log_path)
        print_status("Conversation context cleared.", "33")
    elif command == "/history":
        print_history(conversation)
    return True


def run_cli():
    conversation = []
    log_path = create_session_log_file(model=MODEL, cwd=os.getcwd(), session_label="agent_session")
    print_banner(MODEL, os.getcwd(), log_path)

    while True:
        try:
            query = input(PROMPT)
        except (EOFError, KeyboardInterrupt):
            print()
            append_session_log("session_ended", {"reason": "interrupt"}, log_path)
            print_status("Session ended.", "90")
            break

        trimmed = query.strip()
        if not trimmed:
            print_status("Enter a message, or use /help to view commands.", "33")
            continue

        if is_exit_command(trimmed):
            append_session_log("session_ended", {"reason": "exit"}, log_path)
            print_status("See you next time.", "90")
            break

        if handle_builtin_command(trimmed, conversation, log_path):
            continue

        conversation.append({"role": "user", "content": query})
        append_session_log("user_input", {"content": query}, log_path)
        reply = agent_loop(conversation, render_final=False, log_path=log_path)
        if reply:
            print_assistant_reply(reply)
        else:
            print_status("No displayable text was returned this time.", "33")
        print()


if __name__ == "__main__":
    run_cli()
