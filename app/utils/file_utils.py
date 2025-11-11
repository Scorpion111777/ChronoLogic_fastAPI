import os
import uuid
from app.core.config import settings

def save_result_csv(content: str) -> str:
    filename = f"result_{uuid.uuid4().hex}.csv"
    file_path = os.path.join(settings.OUT_DIR, filename)
    with open(file_path, "w", encoding="utf-8-sig") as f:
        f.write(content)
    return file_path