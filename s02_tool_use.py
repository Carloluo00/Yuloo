import json
import os
import subprocess

from openai import OpenAI

from log import append_session_log, event_to_dict
from terminal import print_assistant_reply, print_status
from tools import TOOLS, TOOL_HANDLERS


MODEL = "qwen3.6-plus"
SYSTEM = f"You are a coding agent at {os.getcwd()}. Use bash to solve tasks. Act, don't explain."

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)




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
            
            handler = TOOL_HANDLERS.get(block.name)
            args = json.loads(block.arguments)
            print_status(f"Running {block.name}: {args}", "90")
            output = handler(**args)
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