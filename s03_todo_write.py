from config import (
    S03_MODEL,
    TODO_REMINDER_INTERVAL as CONFIG_TODO_REMINDER_INTERVAL,
    TODO_REMINDER_MESSAGE as CONFIG_TODO_REMINDER_MESSAGE,
    build_client,
    build_s03_system,
)
from log import append_session_log, event_to_dict
from terminal import print_assistant_reply, print_status
from tools import TOOLS, maybe_add_todo_reminder, run_tool_call as shared_run_tool_call

MODEL = S03_MODEL
TODO_REMINDER_INTERVAL = CONFIG_TODO_REMINDER_INTERVAL
TODO_REMINDER_MESSAGE = CONFIG_TODO_REMINDER_MESSAGE
SYSTEM = build_s03_system()
client = build_client()


def run_tool_call(block, log_path: str | None):
    return shared_run_tool_call(block, log_path)


def agent_loop(conversation: list, render_final: bool = True, log_path: str | None = None):
    print_status(f"Thinking with {MODEL}...", "36")
    rounds_since_todo = 0

    while True:
        response = client.responses.create(
            model=MODEL,
            instructions=SYSTEM,
            input=conversation,
            tools=TOOLS,
            max_output_tokens=8000,
        )

        error = getattr(response, "error", None)
        if error:
            print_status(f"error: {error}", "31")
            return None

        if response.status == "incomplete":
            details = getattr(response, "incomplete_details", "unknown")
            print_status(f"incomplete: {details}", "33")
            if log_path:
                append_session_log(
                    "response_incomplete",
                    {"details": str(details), "output_text": response.output_text},
                    log_path,
                )
            if render_final:
                print_assistant_reply(response.output_text)
            return response.output_text

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

            output = run_tool_call(block, log_path)
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
                print_assistant_reply(response.output_text)
            return response.output_text

        rounds_since_todo = maybe_add_todo_reminder(
            conversation,
            rounds_since_todo,
            used_todo,
            log_path,
            TODO_REMINDER_INTERVAL,
            TODO_REMINDER_MESSAGE,
        )

