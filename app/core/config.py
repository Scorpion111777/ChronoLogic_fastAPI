import os
import tempfile

class Settings:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    STATIC_DIR = os.path.join(BASE_DIR, "static")
    TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
    OUT_DIR = os.path.join(tempfile.gettempdir(), "chronologic_results")

    def __init__(self):
        os.makedirs(self.OUT_DIR, exist_ok=True)

settings = Settings()