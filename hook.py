import json
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from config import PROJECT_ROOT, TRUST_MARKER


class HookEventName(str, Enum):
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    SESSION_START = "SessionStart"


HOOK_EVENTS = tuple(HookEventName)


@dataclass(slots=True)
class HookContext:
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    tool_output: str | None = None
    conversation_size: int | None = None


@dataclass(slots=True)
class HookResult:
    blocked: bool = False
    block_reason: str | None = None
    updated_tool_args: dict[str, Any] | None = None
    messages: list[str] = field(default_factory=list)
    permission_override: dict[str, Any] | None = None


def merge_permission_override(base: dict | None, override: dict | None) -> dict | None:
    if override is None:
        return deepcopy(base) if base is not None else None
    if base is None:
        return deepcopy(override)

    order = {"allow": 0, "ask": 1, "deny": 2}
    base_behavior = str(base.get("behavior", "allow")).lower()
    override_behavior = str(override.get("behavior", "allow")).lower()
    if order.get(override_behavior, 0) >= order.get(base_behavior, 0):
        return deepcopy(override)
    return deepcopy(base)


class HookManager:
    """
    Load and evaluate declarative hooks from .hooks.json.

    Hooks only observe, block, or augment tool calls. They do not execute
    commands or invoke tools themselves.
    """

    def __init__(self, config_path: Path = None, sdk_mode: bool = False):
        self.hooks = {event: [] for event in HOOK_EVENTS}
        self._sdk_mode = sdk_mode
        self.session_started = False
        config_path = config_path or (PROJECT_ROOT / ".hooks.json")
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
                for event in HOOK_EVENTS:
                    event_hooks = config.get("hooks", {}).get(event.value, [])
                    if isinstance(event_hooks, list):
                        self.hooks[event] = event_hooks
                print(f"[Hooks loaded from {config_path}]")
            except Exception as exc:
                print(f"[Hook config error: {exc}]")

    def _check_workspace_trust(self) -> bool:
        if self._sdk_mode:
            return True
        return TRUST_MARKER.exists()

    def _normalize_event(self, event: HookEventName | str) -> HookEventName:
        if isinstance(event, HookEventName):
            return event
        return HookEventName(event)

    def _normalize_context(self, context: HookContext | dict | None) -> HookContext:
        if context is None:
            return HookContext()
        if isinstance(context, HookContext):
            return context
        if isinstance(context, dict):
            return HookContext(
                tool_name=context.get("tool_name"),
                tool_args=context.get("tool_args"),
                tool_output=context.get("tool_output"),
                conversation_size=context.get("conversation_size"),
            )
        raise TypeError(f"Unsupported hook context type: {type(context).__name__}")

    def _matches(self, hook_def: dict, context: HookContext) -> bool:
        matcher = hook_def.get("matcher")
        if not matcher:
            return True
        tool_name = context.tool_name or ""
        return matcher in ("*", tool_name)

    def run_hooks(self, event: HookEventName | str, context: HookContext | dict | None = None) -> HookResult:
        event_name = self._normalize_event(event)
        event_context = self._normalize_context(context)
        result = HookResult()
        if not self._check_workspace_trust():
            return result

        for hook_def in self.hooks.get(event_name, []):
            if not isinstance(hook_def, dict) or not self._matches(hook_def, event_context):
                continue

            log_message = hook_def.get("log_message")
            if log_message:
                print(f"  [hook:{event_name.value}] {str(log_message)[:200]}")

            updated_args = hook_def.get("updated_args")
            if updated_args is not None:
                result.updated_tool_args = deepcopy(updated_args)

            additional_context = hook_def.get("additional_context")
            if additional_context:
                result.messages.append(str(additional_context))

            permission_decision = hook_def.get("permission_decision")
            if isinstance(permission_decision, dict):
                result.permission_override = merge_permission_override(
                    result.permission_override,
                    permission_decision,
                )

            if hook_def.get("block"):
                result.blocked = True
                result.block_reason = str(hook_def.get("block_reason") or "Blocked by hook")
                print(f"  [hook:{event_name.value}] BLOCKED: {result.block_reason[:200]}")
                break

        return result
