from datetime import datetime
import json
import os

from config import LOG_DIR as CONFIG_LOG_DIR

DEFAULT_LOG_DIR = str(CONFIG_LOG_DIR)


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
    # Normalize SDK objects in descending order of fidelity before falling back to a string snapshot.
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
    log_dir: str = DEFAULT_LOG_DIR,
    session_label: str = "session",
    metadata: dict | None = None,
) -> str:
    os.makedirs(log_dir, exist_ok=True)
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    log_path = os.path.join(log_dir, f"{session_label}_{session_id}.jsonl")
    current_cwd = cwd or os.getcwd()
    # Touch the file early so the banner can point at a path that already exists.
    with open(log_path, "a", encoding="utf-8"):
        pass
    payload = {"session_id": session_id, "model": model, "cwd": current_cwd}
    if metadata:
        payload.update(metadata)
    append_session_log(
        "session_started",
        payload,
        log_path,
    )
    return log_path
