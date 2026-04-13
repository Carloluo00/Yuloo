import json
import subprocess

from config import (
    DEFAULT_MODEL,
    DANGEROUS_SHELL_PATTERNS,
    SHELL_TIMEOUT_SECONDS,
    TOOL_OUTPUT_CHAR_LIMIT,
    build_client,
    build_s01_system,
)
from log import append_session_log, event_to_dict
from terminal import print_assistant_reply, print_status


MODEL = DEFAULT_MODEL
SYSTEM = build_s01_system()
client = build_client()

TOOLS = [
    {
        "type": "function",
        "name": "bash",
        "description": "Run a command in the current OS shell. On Windows, this is cmd.",
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    }
]


def run_bash(command: str) -> str:
    if any(item in command for item in DANGEROUS_SHELL_PATTERNS):
        return "Error: Dangerous command blocked."
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=None,
            capture_output=True,
            text=True,
            timeout=SHELL_TIMEOUT_SECONDS,
        )
        output = (result.stdout + result.stderr).strip()
        return output[:TOOL_OUTPUT_CHAR_LIMIT] if output else "(no output)"
    except subprocess.TimeoutExpired:
        return f"Error: Timeout ({SHELL_TIMEOUT_SECONDS}s)"
    except (FileNotFoundError, OSError) as exc:
        return f"Error: {exc}"


def agent_loop(conversation: list, render_final: bool = True, log_path: str | None = None):
    print_status(f"Thinking with {MODEL}...", "36")

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
        for block in response.output:
            if block.type != "function_call":
                continue

            args = json.loads(block.arguments)
            command = args["command"]
            preview = command if len(command) <= 80 else f"{command[:77]}..."
            print_status(f"Running bash: {preview}", "90")
            output = run_bash(command)
            if output.startswith("Error:"):
                print_status(output, "31")

            tool_result = {
                "type": "function_call_output",
                "call_id": block.call_id,
                "output": output,
            }
            results.append(tool_result)
            if log_path:
                append_session_log("tool_result", tool_result, log_path)

        # Feed tool outputs back into the transcript so the next model turn can use them.
        conversation += results

        if not results:
            if render_final:
                print_assistant_reply(response.output_text)
            return response.output_text
