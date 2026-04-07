import json
import os
import subprocess
from utils import safe_path
from log import append_session_log, event_to_dict
from terminal import print_assistant_reply, print_status, print_todo_state
from openai import OpenAI
from pathlib import Path


WORKDIR = Path.cwd()
MODEL = "qwen3.6-plus"
SUBAGENT_SYSTEM = f"You are a coding subagent at {WORKDIR}. Complete the given task, then summarize your findings."
client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

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
        return "\n".join(lines)[:50000]
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

def run_subagent(prompt: str) -> str:
    sub_conversation = [{"role": "user", "content": prompt}]  # fresh context
    for _ in range(30):  # safety limit
        response = client.messages.create(
            model=MODEL, instructions=SUBAGENT_SYSTEM, input=sub_conversation,
            tools=TOOLS, max_output_tokens=8000,
        )
        response_blocks = [event_to_dict(block) for block in response.output]
        sub_conversation += response_blocks

        results = []
        for block in response.content:
            if block.type != "function_call":
                continue
            handler = TOOL_HANDLERS.get(block.name)
            output = handler(**json.loads(block.arguments)) if handler else f"Error: Unknown tool '{block.name}'"
            results.append({"type": "function_call_output", "call_id": block.call_id, "output": output})
        
        if not results:
            break
        sub_conversation += results
    return "".join(b.text for b in response.content if hasattr(b, "text")) or "(no summary)"



def run_tool_call(block, log_path: str | None):
    args = json.loads(block.arguments)
    print_status(f"Running {block.name}: {args}", "90")

    # run subagents
    if block.name == "task":
        desc = block.arguments.get("description", "subtask")
        prompt = block.arguments.get("prompt", "")
        print_status(f"Spawning subagent for {desc}...", "80")
        output = run_subagent(prompt)


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