import json
import subprocess
from uuid import uuid4
from config import (
    DANGEROUS_SHELL_PATTERNS,
    SHELL_TIMEOUT_SECONDS,
    SUBAGENT_MAX_TURNS,
    SUBAGENT_MODEL,
    TOOL_OUTPUT_CHAR_LIMIT,
    build_client,
    build_subagent_system,
)
from utils import safe_path
from log import append_session_log, event_to_dict
from terminal import print_status, print_todo_state

MODEL = SUBAGENT_MODEL
SUBAGENT_SYSTEM = build_subagent_system()
client = build_client()

TOOL_HANDLERS = {
    "bash":       lambda **kw: run_bash(kw["command"]),
    "read_file":  lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":  lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    "todo":       lambda **kw: TODO.update(kw["items"]),
}

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
    },
    {
        "type": "function",
        "name": "read_file",
        "description": "Read file contents. Give priority to using this function when you need to read files.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["path"],
        },
    },
    {
        "type": "function",
        "name": "write_file",
        "description": "Write content to file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "type": "function",
        "name": "edit_file",
        "description": "Replace exact text in file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_text": {"type": "string"},
                "new_text": {"type": "string"},
            },
            "required": ["path", "old_text", "new_text"],
        },
    },
    {
        "type": "function",
        "name": "todo",
        "description": "Manage a todo list. Update task list. Track progress on multi-step tasks.",
        "parameters": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "text": {"type": "string"},
                            "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                        },
                        "required": ["id", "text", "status"]
                    },
                },
            },
            "required": ["items"],
        },
    },
]

PARENT_TOOLS = TOOLS + [
    {
        "type": "function",
        "name": "task",
        "description": "Spawn a subagent with fresh context. It shares the filesystem but not conversation history.",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
                "description": {"type": "string", "description": "Short description of the task."},
            },
            "required": ["prompt"],
        },
    },
]

def run_bash(command: str) -> str:
    if any(item in command for item in DANGEROUS_SHELL_PATTERNS):
        return "Error: Dangerous command blocked."
    try:
        result = subprocess.run(
            command,
            shell=True,
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
    
def run_read(path: str, limit: int = None) -> str:
    try:
        p = safe_path(path)
        try:
            text = p.read_text(encoding="utf-8") # 优先使用 utf-8
        except UnicodeDecodeError:
            text = p.read_text(encoding="gbk", errors="replace") # 兼容一些非 utf-8 文件（如 Windows 常见编码）
        lines = text.splitlines()
        if limit and len(lines) > limit:
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)[:TOOL_OUTPUT_CHAR_LIMIT]
    except Exception as e:
        return f"Error: {e}"

def run_write(path: str, content: str) -> str:
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"

def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        fp = safe_path(path)
        content = fp.read_text()
        if old_text not in content:
            return f"Error: Text not found in {path}"
        fp.write_text(content.replace(old_text, new_text, 1))
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"
    
class TodoManager:
    def __init__(self):
        self.items = []

    def update(self, items: list) -> str:
        if len(items) > 20:
            raise ValueError("Max 20 todos allowed")
        validated = []
        in_progress_count = 0
        for i, item in enumerate(items):
            text = str(item.get("text", "")).strip()
            status = str(item.get("status", "pending")).lower()
            item_id = str(item.get("id", str(i + 1)))
            if not text:
                raise ValueError(f"Item {item_id}: text required")
            if status not in ("pending", "in_progress", "completed"):
                raise ValueError(f"Item {item_id}: invalid status '{status}'")
            if status == "in_progress":
                in_progress_count += 1
            validated.append({"id": item_id, "text": text, "status": status})
        if in_progress_count > 1:
            raise ValueError("Only one task can be in_progress at a time")
        self.items = validated
        return self.render()
    
    def render(self) -> str:
        if not self.items:
            return "No todos."
        lines = []
        for item in self.items:
            marker = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}[item["status"]]
            lines.append(f"{marker} #{item['id']}: {item['text']}")
        done = sum(1 for t in self.items if t["status"] == "completed")
        lines.append(f"\n({done}/{len(self.items)} completed)")
        return "\n".join(lines)

TODO = TodoManager()

def extract_response_text(response) -> str:
    output_text = getattr(response, "output_text", "")
    if output_text:
        return output_text

    parts = []
    for block in getattr(response, "output", []):
        if hasattr(block, "text"):
            parts.append(block.text)
            continue
        content = getattr(block, "content", None)
        if not isinstance(content, list):
            continue
        for item in content:
            text = getattr(item, "text", "")
            if text:
                parts.append(text)
    return "".join(parts)


def run_subagent(
    prompt: str,
    log_path: str | None = None,
    parent_call_id: str | None = None,
    description: str | None = None,
) -> str:
    sub_conversation = [{"role": "user", "content": prompt}]  # fresh context
    subagent_id = f"subagent_{uuid4().hex[:8]}"
    total_turns = 0
    summary = "(no summary)"

    if log_path:
        append_session_log(
            "subagent_started",
            {
                "subagent_id": subagent_id,
                "parent_call_id": parent_call_id,
                "description": description or "subtask",
                "prompt": prompt,
            },
            log_path,
        )

    for turn in range(1, SUBAGENT_MAX_TURNS + 1):  # safety limit
        total_turns = turn
        response = client.responses.create(
            model=MODEL, instructions=SUBAGENT_SYSTEM, input=sub_conversation,
            tools=TOOLS, max_output_tokens=8000,
        )
        response_blocks = [event_to_dict(block) for block in response.output]
        sub_conversation += response_blocks
        summary = extract_response_text(response) or summary

        if log_path:
            append_session_log(
                "subagent_response",
                {
                    "subagent_id": subagent_id,
                    "parent_call_id": parent_call_id,
                    "turn": turn,
                    "output_text": summary,
                    "blocks": response_blocks,
                },
                log_path,
            )

        results = []
        for block in response.output:
            if block.type != "function_call":
                continue
            handler = TOOL_HANDLERS.get(block.name)
            args = json.loads(block.arguments)
            try:
                output = handler(**args) if handler else f"Error: Unknown tool '{block.name}'"
            except Exception as exc:
                output = f"Error: {exc}"
            results.append({"type": "function_call_output", "call_id": block.call_id, "output": output})

            if log_path:
                append_session_log(
                    "subagent_tool_result",
                    {
                        "subagent_id": subagent_id,
                        "parent_call_id": parent_call_id,
                        "turn": turn,
                        "call_id": block.call_id,
                        "name": block.name,
                        "args": args,
                        "output": output,
                        "ok": not output.startswith("Error:"),
                    },
                    log_path,
                )
        
        if not results:
            break
        sub_conversation += results

    if log_path:
        append_session_log(
            "subagent_finished",
            {
                "subagent_id": subagent_id,
                "parent_call_id": parent_call_id,
                "description": description or "subtask",
                "turns": total_turns,
                "summary": summary,
            },
            log_path,
        )

    return summary



def run_tool_call(block, log_path: str | None):
    args = json.loads(block.arguments)
    print_status(f"Running {block.name}: {args}", "90")

    # run subagents
    if block.name == "task":
        desc = args.get("description", "subtask")
        prompt = args.get("prompt", "")
        print_status(f"Spawning subagent for {desc}...", "80")
        output = run_subagent(
            prompt,
            log_path=log_path,
            parent_call_id=block.call_id,
            description=desc,
        )
    else:
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
