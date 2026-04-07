import json
import os
import subprocess

from openai import OpenAI

from s01_logging import append_session_log, event_to_dict
from s01_terminal import print_assistant_reply, print_status


MODEL = "qwen3.6-plus"
SYSTEM = f"You are a coding agent at {os.getcwd()}. Use bash to solve tasks. Act, don't explain."

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

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
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(item in command for item in dangerous):
        return "Error: Dangerous command blocked."
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = (result.stdout + result.stderr).strip()
        return output[:50000] if output else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
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

        conversation += results

        if not results:
            if render_final:
                print_assistant_reply(response.output_text)
            return response.output_text
