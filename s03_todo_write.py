import json
import os
import subprocess
from pathlib import Path

from openai import OpenAI

from log import append_session_log, event_to_dict
from terminal import print_assistant_reply, print_status, print_todo_state
from tools import TOOLS, TOOL_HANDLERS

WORKDIR = Path.cwd()
MODEL = "qwen3.6-plus"
TODO_REMINDER_INTERVAL = 3
TODO_REMINDER_MESSAGE = "Reminder: update your todo list if task status changed."
SYSTEM = (
    f"You are a coding agent at {WORKDIR}. "
    "Always plan first. Use the todo tool to plan multi-step tasks. "
    "Mark a task in_progress before starting it and completed when done."
)

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)


def run_tool_call(block, log_path: str | None):
    args = json.loads(block.arguments)
    print_status(f"Running {block.name}: {args}", "90")

    handler = TOOL_HANDLERS.get(block.name)
    if handler is None:
        error = f"Unknown tool '{block.name}'"
        output = f"Error: {error}"
        print_status(output, "31")
        if log_path:
            append_session_log("tool_error", {"name": block.name, "args": args, "error": error}, log_path)
        return output

    try:
        output = handler(**args)
    except Exception as exc:
        output = f"Error: {exc}"
        print_status(f"{block.name} failed: {exc}", "31")
        if log_path:
            append_session_log("tool_error", {"name": block.name, "args": args, "error": str(exc)}, log_path)

    if block.name == "todo":
        print_todo_state(output)
        if log_path:
            append_session_log(
                "todo_updated",
                {
                    "items": args.get("items", []),
                    "output": output,
                    "ok": not output.startswith("Error:"),
                },
                log_path,
            )

    return output




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

        rounds_since_todo = 0 if used_todo else rounds_since_todo + 1
        if rounds_since_todo >= TODO_REMINDER_INTERVAL:
            conversation.append({"role": "user", "content": TODO_REMINDER_MESSAGE})
            print_status("Injected todo reminder for the agent.", "33")
            if log_path:
                append_session_log(
                    "todo_reminder",
                    {"message": TODO_REMINDER_MESSAGE, "rounds_since_todo": rounds_since_todo},
                    log_path,
                )
            rounds_since_todo = 0


