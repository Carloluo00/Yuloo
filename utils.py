from pathlib import Path

from config import WORKDIR


def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path

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

def _read_text_with_fallback(path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="gbk", errors="replace")