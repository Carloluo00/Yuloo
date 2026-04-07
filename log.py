from datetime import datetime
import json
import os


LOG_DIR = os.path.join(os.getcwd(), "logs")


def append_session_log(event: str, payload: dict, log_path: str):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "event": event,
        "payload": payload,
    }
    with open(log_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def event_to_dict(event) -> dict:
    if isinstance(event, dict):
        return event
    if hasattr(event, "to_dict"):
        return event.to_dict()
    if hasattr(event, "__dict__"):
        return {
            key: value
            for key, value in event.__dict__.items()
            if not key.startswith("_")
        }
    return {"value": str(event)}


def create_session_log_file(
    model: str = "unknown",
    cwd: str | None = None,
    log_dir: str = LOG_DIR,
    session_label: str = "session",
) -> str:
    os.makedirs(log_dir, exist_ok=True)
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    log_path = os.path.join(log_dir, f"{session_label}_{session_id}.jsonl")
    current_cwd = cwd or os.getcwd()
    with open(log_path, "a", encoding="utf-8"):
        pass
    append_session_log(
        "session_started",
        {"session_id": session_id, "model": model, "cwd": current_cwd},
        log_path,
    )
    return log_path
