import json
import subprocess
import re
from dataclasses import dataclass
from pathlib import Path
from copy import deepcopy
from json import JSONDecodeError
from uuid import uuid4
from config import (
    DEFAULT_MODEL,
    SKILLS_DIR,
    DANGEROUS_SHELL_PATTERNS,
    SHELL_TIMEOUT_SECONDS,
    SUBAGENT_MAX_TURNS,
    TOOL_OUTPUT_CHAR_LIMIT,
    build_client,
    build_subagent_system,
)
from utils import safe_path, extract_response_text, _read_text_with_fallback
from log import append_session_log, event_to_dict
from terminal import print_skill_state, print_status, print_todo_state

MODEL = DEFAULT_MODEL
SUBAGENT_SYSTEM = build_subagent_system()
client = build_client()

TOOL_HANDLERS = {
    "bash":       lambda **kw: run_bash(kw["command"]),
    "read_file":  lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":  lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    "todo":       lambda **kw: TODO.update(kw["items"]),
    "load_skill": lambda **kw: SKILL_REGISTRY.load_full_text(kw["name"]),
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
        "description": (
            "Manage a todo list for multi-step tasks. "
            "Pass items as a native JSON array in the function arguments, never a quoted string. "
            'Example: {"items":[{"id":"1","text":"Inspect logs","status":"in_progress"}]}'
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "description": (
                        "Native JSON array of todo objects. Do not stringify this array. "
                        'Use [{"id":"1","text":"Inspect logs","status":"in_progress"}], not "[...]"'
                    ),
                    "maxItems": 20,
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "text": {"type": "string"},
                            "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                        },
                        "required": ["id", "text", "status"],
                    },
                },
            },
            "required": ["items"],
        },
    },
    {
        "type": "function",
        "name": "load_skill",
        "description": "Load the full body of a named skill into the current context.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
        },
    },
]

PARENT_TOOLS = TOOLS + [
    {
        "type": "function",
        "name": "task",
        "description": "Spawn a subagent that inherits the parent conversation context, then receives a delegated task prompt.",
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
        text = _read_text_with_fallback(p)
        lines = text.splitlines()
        if limit and len(lines) > limit:
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)[:TOOL_OUTPUT_CHAR_LIMIT]
    except Exception as exc:
        return f"Error: {exc}"

def run_write(path: str, content: str) -> str:
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as exc:
        return f"Error: {exc}"

def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        fp = safe_path(path)
        content = fp.read_text()
        if old_text not in content:
            return f"Error: Text not found in {path}"
        fp.write_text(content.replace(old_text, new_text, 1))
        return f"Edited {path}"
    except Exception as exc:
        return f"Error: {exc}"
    
class TodoManager:
    def __init__(self):
        self.items = []

    def _normalize_items(self, items) -> list[dict]:
        if isinstance(items, str):
            try:
                items = json.loads(items)
            except JSONDecodeError as exc:
                raise ValueError(
                    "todo.items was a string but not valid JSON. "
                    'Pass a native JSON array like {"items":[...]} instead of quoting the array.'
                ) from exc

        if not isinstance(items, list):
            raise ValueError(
                f"todo.items must be a JSON array of todo objects, got {type(items).__name__}"
            )

        return items

    def update(self, items) -> str:
        items = self._normalize_items(items)
        if len(items) > 20:
            raise ValueError(f"todo.items may contain at most 20 entries; received {len(items)}")
        validated = []
        in_progress_count = 0
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                raise ValueError(
                    f"todo.items[{i}] must be an object with id/text/status, got {type(item).__name__}"
                )
            text = str(item.get("text", "")).strip()
            status = str(item.get("status", "pending")).lower()
            item_id = str(item.get("id", str(i + 1)))
            if not text:
                raise ValueError(f"todo.items[{i}] (id={item_id}): text is required")
            if status not in ("pending", "in_progress", "completed"):
                raise ValueError(
                    f"todo.items[{i}] (id={item_id}): invalid status '{status}'. "
                    "Expected pending, in_progress, or completed"
                )
            if status == "in_progress":
                in_progress_count += 1
            validated.append({"id": item_id, "text": text, "status": status})
        if in_progress_count > 1:
            raise ValueError("todo.items can contain only one in_progress entry at a time")
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

def maybe_add_todo_reminder(
    conversation: list,
    rounds_since_todo: int,
    used_todo: bool,
    log_path: str | None,
    reminder_interval: int,
    reminder_message: str,
) -> int:
    rounds_since_todo = 0 if used_todo else rounds_since_todo + 1
    if rounds_since_todo < reminder_interval:
        return rounds_since_todo

    conversation.append({"role": "user", "content": reminder_message})
    print_status("Injected todo reminder for the agent.", "33")
    if log_path:
        append_session_log(
            "todo_reminder",
            {"message": reminder_message, "rounds_since_todo": rounds_since_todo},
            log_path,
        )
    return 0





def run_subagent(
    prompt: str,
    log_path: str | None = None,
    parent_call_id: str | None = None,
    description: str | None = None,
    parent_conversation: list | None = None,
) -> str:
    sub_conversation = deepcopy(parent_conversation) if parent_conversation else []
    sub_conversation.append({"role": "user", "content": prompt})
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
                "inherited_messages": len(parent_conversation or []),
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



def run_tool_call(block, log_path: str | None, parent_conversation: list | None = None):
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
            parent_conversation=parent_conversation,
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
        elif block.name == "load_skill":
            skill_name = args.get("name", "").strip()
            manifest = SKILL_REGISTRY.get_manifest(skill_name)
            ok = not output.startswith("Error:")
            if ok and manifest:
                print_skill_state(manifest.name, manifest.description, str(manifest.path))
            else:
                print_status(output, "31")
            if log_path:
                append_session_log(
                    "skill_loaded",
                    {
                        "name": skill_name,
                        "ok": ok,
                        "path": str(manifest.path) if manifest else None,
                        "description": manifest.description if manifest else None,
                    },
                    log_path,
                )

    return output


@dataclass
class SkillManifest:
    name: str
    description: str
    path: Path

@dataclass
class SkillDocument:
    manifest: SkillManifest
    body: str

class SkillRegistry:
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.documents: dict[str, SkillDocument] = {}
        self._load_all()

    def _load_all(self) -> None:
        if not self.skills_dir.exists():
            return

        for path in sorted(self.skills_dir.rglob("SKILL.md")):
            meta, body = self._parse_frontmatter(_read_text_with_fallback(path))
            name = meta.get("name", path.parent.name)
            description = meta.get("description", "No description")
            manifest = SkillManifest(name=name, description=description, path=path)
            self.documents[name] = SkillDocument(manifest=manifest, body=body.strip())

    def _parse_frontmatter(self, text: str) -> tuple[dict, str]:
        match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
        if not match:
            return {}, text

        meta = {}
        for line in match.group(1).strip().splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip("\"'")
        return meta, match.group(2)

    def count(self) -> int:
        return len(self.documents)

    def get_manifest(self, name: str) -> SkillManifest | None:
        document = self.documents.get(name)
        return document.manifest if document else None

    def describe_available(self) -> str:
        if not self.documents:
            return "(no skills available)"
        lines = []
        for name in sorted(self.documents):
            manifest = self.documents[name].manifest
            lines.append(f"- {manifest.name}: {manifest.description}")
        return "\n".join(lines)

    def load_full_text(self, name: str) -> str:
        document = self.documents.get(name)
        if not document:
            known = ", ".join(sorted(self.documents)) or "(none)"
            return f"Error: Unknown skill '{name}'. Available skills: {known}"

        return (
            f"<skill name=\"{document.manifest.name}\">\n"
            f"{document.body}\n"
            "</skill>"
        )

SKILL_REGISTRY = SkillRegistry(SKILLS_DIR)
