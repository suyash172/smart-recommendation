import json
import os
from pathlib import Path
from typing import Any

# mock-bank-api/app/seed_loader.py -> repo root is parents[2]
DEFAULT_SEED_PATH = Path(__file__).resolve().parents[2] / "data" / "mock-bank-api" / "mock_bank_seed_data.json"


def load_seed(path: str | Path | None = None) -> dict[str, Any]:
    seed_path = Path(path or os.getenv("MOCK_SEED_PATH") or DEFAULT_SEED_PATH)
    return json.loads(seed_path.read_text(encoding="utf-8-sig"))