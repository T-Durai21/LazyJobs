import re
from pathlib import Path

from .config import settings


def save_cv(user_id: int, filename: str, data: bytes) -> Path:
    # Keep the original so a later parser fix can be re-run without asking for a new upload.
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", Path(filename).name)
    folder = Path(settings.upload_dir) / str(user_id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / safe_name
    path.write_bytes(data)
    return path
