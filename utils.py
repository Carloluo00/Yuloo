import os
import subprocess
from pathlib import Path


WORKDIR = Path.cwd()

def safe_path(p: str) -> str:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path