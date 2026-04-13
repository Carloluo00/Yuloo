import json

from config import (
    DEFAULT_MODEL,
    TODO_REMINDER_INTERVAL as CONFIG_TODO_REMINDER_INTERVAL,
    TODO_REMINDER_MESSAGE as CONFIG_TODO_REMINDER_MESSAGE,
    build_client,
    build_s06_system,
)
from log import append_session_log, event_to_dict
from terminal import print_assistant_reply, print_status
from tools import (
    SKILL_REGISTRY,
    CompactState,
    PARENT_TOOLS,
    compact_history,
    maybe_add_todo_reminder,
    maybe_compact_history,
    micro_compact,
    persist_large_output,
    run_tool_call,
    track_recent_file,
)
from utils import extract_response_text


MODEL = DEFAULT_MODEL
TODO_REMINDER_INTERVAL = CONFIG_TODO_REMINDER_INTERVAL
TODO_REMINDER_MESSAGE = CONFIG_TODO_REMINDER_MESSAGE
RUNTIME_NAME = "s06_compact"
SESSION_LABEL = "compact_agent_session"
AVAILABLE_SKILLS_TEXT = SKILL_REGISTRY.describe_available()
SYSTEM = f"{build_s06_system()}\n\nAvailable skills:\n{AVAILABLE_SKILLS_TEXT}"
client = build_client()


def agent_loop(conversation: list, render_final: bool = True, log_path: str | None = None):
    print_status(f"Thinking with {MODEL}...", "36")
    rounds_since_todo = 0
    compact_state = CompactState()

    while True:
        # Trim stale tool chatter before asking the model to spend tokens on it.
        conversation[:] = micro_compact(conversation)
        conversation[:] = maybe_compact_history(conversation, compact_state, log_path=log_path)

        response = client.responses.create(
            model=MODEL,
            instructions=SYSTEM,
            input=conversation,
            tools=PARENT_TOOLS,
            max_output_tokens=8000,
        )

        error = getattr(response, "error", None)
        if error:
            print_status(f"error: {error}", "31")
            return None

        reply_text = extract_response_text(response)
        if response.status == "incomplete":
            details = getattr(response, "incomplete_details", "unknown")
            print_status(f"incomplete: {details}", "33")
            if log_path:
                append_session_log(
                    "response_incomplete",
                    {"details": str(details), "output_text": reply_text},
                    log_path,
                )
            if render_final:
                print_assistant_reply(reply_text)
            return reply_text

        response_blocks = [event_to_dict(block) for block in response.output]
        conversation += response_blocks
        if log_path:
            for block_dict in response_blocks:
                append_session_log("assistant_response", block_dict, log_path)

        results = []
        used_todo = False
        for block in response.output:
            if block.type != "function_call":
                continue

            try:
                tool_args = json.loads(block.arguments)
            except json.JSONDecodeError:
                tool_args = {}

            file_path = tool_args.get("path")
            if isinstance(file_path, str) and file_path.strip():
                track_recent_file(compact_state, file_path.strip())

            output = run_tool_call(block, log_path, parent_conversation=conversation)
            tool_result = {
                "type": "function_call_output",
                "call_id": block.call_id,
                "output": output,
            }
            if block.name == "todo":
                used_todo = True
            results.append(tool_result)
            if log_path:
                append_session_log("tool_result", tool_result, log_path)

        conversation += results
        if not results:
            if render_final:
                print_assistant_reply(reply_text)
            return reply_text

        rounds_since_todo = maybe_add_todo_reminder(
            conversation,
            rounds_since_todo,
            used_todo,
            log_path,
            TODO_REMINDER_INTERVAL,
            TODO_REMINDER_MESSAGE,
        )
