import re
from pathlib import Path
import json
from fnmatch import fnmatch
from config import TRUST_MARKER, WORKDIR


MODES = ("default", "plan", "auto")
READ_ONLY_TOOLS = {"read_file", "load_skill", "todo"}
WRITE_TOOLS = {"write_file", "edit_file", "bash", "task"}

# -- Permission rules --
DEFAULT_RULES = [
    # Always deny dangerous patterns
    {"tool": "bash", "content": "rm -rf /", "behavior": "deny"},
    {"tool": "bash", "content": "sudo *", "behavior": "deny"},
    # Allow reading anything
    {"tool": "read_file", "path": "*", "behavior": "allow"},
    {"tool": "load_skill", "behavior": "allow"},
    {"tool": "todo", "behavior": "allow"},
]

class BashSecurityValidator:
    """
    Validate bash commands for obviously dangerous patterns.
    """
    VALIDATORS = [
        ("shell_metachar", r"[;&|`$]"),       # shell metacharacters
        ("sudo", r"\bsudo\b"),                 # privilege escalation
        ("rm_rf", r"\brm\s+(-[a-zA-Z]*)?r"),  # recursive delete
        ("cmd_substitution", r"\$\("),          # command substitution
        ("ifs_injection", r"\bIFS\s*="),        # IFS manipulation
    ]

    def validate(self, command: str) -> list:
        """
        Check a bash command against all validators.

        Returns list of (validator_name, matched_pattern) tuples for failures.
        An empty list means the command passed all validators.
        """
        failures = []
        for name, pattern in self.VALIDATORS:
            if re.search(pattern, command):
                failures.append((name, pattern))
        return failures

    def is_safe(self, command: str) -> bool:
        """Convenience: returns True only if no validators triggered."""
        return len(self.validate(command)) == 0

    def describe_failures(self, command: str) -> str:
        """Human-readable summary of validation failures."""
        failures = self.validate(command)
        if not failures:
            return "No issues detected"
        parts = [f"{name} (pattern: {pattern})" for name, pattern in failures]
        return "Security flags: " + ", ".join(parts)
    
def is_workspace_trusted(workspace: Path = None) -> bool:
    """
    Check if a workspace has been explicitly marked as trusted.
    """
    ws = workspace or WORKDIR
    if ws == WORKDIR:
        return TRUST_MARKER.exists()
    return (ws / TRUST_MARKER.relative_to(WORKDIR)).exists()


bash_validator = BashSecurityValidator()

class PermissionManager:
    """
    Manages permission decisions for tool calls.

    Pipeline: deny_rules -> mode_check -> allow_rules -> ask_user
    """

    def __init__(self, mode: str = "default", rules: list = None):
        if mode not in MODES:
            raise ValueError(f"Unknown mode: {mode}. Choose from {MODES}")
        self.mode = mode
        self.rules = rules or list(DEFAULT_RULES)
        # Simple denial tracking helps surface when the agent is repeatedly
        # asking for actions the system will not allow.
        self.consecutive_denials = 0
        self.max_consecutive_denials = 3

    def check(self, tool_name: str, tool_args: dict) -> dict:
        """
        Returns: {"behavior": "allow"|"deny"|"ask", "reason": str}
        """
        bash_failures = []
        # Step 0: Bash security validation for bypass-immune severe patterns.
        if tool_name == "bash":
            command = tool_args.get("command", "")
            bash_failures = bash_validator.validate(command)
            if bash_failures:
                severe = {"sudo", "rm_rf"}
                severe_hits = [f for f in bash_failures if f[0] in severe]
                if severe_hits:
                    desc = bash_validator.describe_failures(command)
                    return {"behavior": "deny",
                            "reason": f"Bash validator: {desc}"}

        # Step 1: Deny rules (bypass-immune, checked first always)
        for rule in self.rules:
            if rule["behavior"] != "deny":
                continue
            if self._matches(rule, tool_name, tool_args):
                return {"behavior": "deny",
                        "reason": f"Blocked by deny rule: {rule}"}

        # Step 2: Mode-based decisions
        if self.mode == "plan":
            # Plan mode: deny all write operations, allow reads
            if tool_name in WRITE_TOOLS:
                return {"behavior": "deny",
                        "reason": "Plan mode: write operations are blocked"}
            return {"behavior": "allow", "reason": "Plan mode: read-only allowed"}

        if self.mode == "auto":
            # Auto mode: auto-allow read-only tools, ask for writes
            if tool_name in READ_ONLY_TOOLS:
                return {"behavior": "allow",
                        "reason": "Auto mode: read-only tool auto-approved"}
            # Teaching: fall through to allow rules, then ask
            pass

        # Step 3: Allow rules
        for rule in self.rules:
            if rule["behavior"] != "allow":
                continue
            if self._matches(rule, tool_name, tool_args):
                self.consecutive_denials = 0
                return {"behavior": "allow",
                        "reason": f"Matched allow rule: {rule}"}

        if bash_failures:
            desc = bash_validator.describe_failures(tool_args.get("command", ""))
            return {"behavior": "ask",
                    "reason": f"Bash validator flagged: {desc}"}

        # Step 4: Ask user (default behavior for unmatched tools)
        return {"behavior": "ask",
                "reason": f"No rule matched for {tool_name}, asking user"}

    def ask_user(self, tool_name: str, tool_args: dict) -> bool:
        """Interactive approval prompt. Returns True if approved."""
        preview = json.dumps(tool_args, ensure_ascii=False)[:200]
        print(f"\n  [Permission] {tool_name}: {preview}")
        try:
            answer = input("  Allow? (y/n/always): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False

        if answer == "always":
            # Persist the smallest practical allow rule for future prompts.
            rule = {"tool": tool_name, "behavior": "allow"}
            if tool_args.get("path"):
                rule["path"] = tool_args["path"]
            elif tool_args.get("command"):
                rule["content"] = tool_args["command"]
            self.rules.append(rule)
            self.consecutive_denials = 0
            return True
        if answer in ("y", "yes"):
            self.consecutive_denials = 0
            return True

        # Track denials for circuit breaker
        self.consecutive_denials += 1
        if self.consecutive_denials >= self.max_consecutive_denials:
            print(f"  [{self.consecutive_denials} consecutive denials -- "
                  "consider switching to plan mode]")
        return False

    def _matches(self, rule: dict, tool_name: str, tool_args: dict) -> bool:
        """Check if a rule matches the tool call."""
        # Tool name match
        if rule.get("tool") and rule["tool"] != "*":
            if rule["tool"] != tool_name:
                return False
        # Path pattern match
        if "path" in rule and rule["path"] != "*":
            path = tool_args.get("path", "")
            if not fnmatch(path, rule["path"]):
                return False
        # Content pattern match (for bash commands)
        if "content" in rule:
            command = tool_args.get("command", "")
            if not fnmatch(command, rule["content"]):
                return False
        return True
