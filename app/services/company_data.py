from pathlib import Path
import json

_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "companies.json"


def load_company(company_id: str) -> dict:
    if not _DATA_PATH.exists():
        return {}
    data = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    if data.get("company_id") == company_id:
        return data
    return {}
