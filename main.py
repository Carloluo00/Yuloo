import os

from config import WORKDIR
from hook import HookManager
from log import append_session_log, create_session_log_file
from permission import PermissionManager
from s08_hook import AVAILABLE_SKILLS_TEXT, MODEL, RUNTIME_NAME, SESSION_LABEL, agent_loop
from terminal import print_assistant_reply, print_banner, print_status
from utils import count_available_skills, handle_builtin_command, is_exit_command


PROMPT = "\033[36muser >> \033[0m"


def run_cli():
    os.chdir(WORKDIR)
    conversation = []
    perms = PermissionManager()
    hooks = HookManager()
    skill_count = count_available_skills(AVAILABLE_SKILLS_TEXT)
    log_path = create_session_log_file(
        model=MODEL,
        cwd=str(WORKDIR),
        session_label=SESSION_LABEL,
        metadata={"runtime": RUNTIME_NAME, "skills_available": skill_count},
    )
    print_banner(
        MODEL,
        str(WORKDIR),
        log_path,
        runtime_name=RUNTIME_NAME,
        skills_available=skill_count,
    )

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

        if handle_builtin_command(
            trimmed,
            conversation,
            log_path,
            model=MODEL,
            runtime_name=RUNTIME_NAME,
            available_skills_text=AVAILABLE_SKILLS_TEXT,
            cwd=str(WORKDIR),
        ):
            # Built-ins are handled locally and should not consume a model turn.
            continue

        conversation.append({"role": "user", "content": query})
        append_session_log("user_input", {"content": query}, log_path)
        reply = agent_loop(conversation, render_final=False, log_path=log_path, perms=perms, hooks=hooks)
        if reply:
            print_assistant_reply(reply)
        else:
            print_status("No displayable text was returned this time.", "33")
        print()


if __name__ == "__main__":
    run_cli()
