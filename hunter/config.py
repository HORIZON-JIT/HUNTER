import os
from pathlib import Path

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

DEFAULT_MODEL = "sonnet"

OUTPUT_DIR = Path("output")
