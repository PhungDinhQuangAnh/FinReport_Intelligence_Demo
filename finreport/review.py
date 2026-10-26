"""Human-in-the-loop review storage. Designed for Streamlit local demo usage."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from .config import OUTPUTS

REVIEW_PATH = OUTPUTS / "human_reviews.csv"
REVIEW_COLUMNS = ["company_id", "fiscal_year", "decision", "reviewer", "comment", "reviewed_at_utc"]


def load_reviews(path: Path = REVIEW_PATH) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=REVIEW_COLUMNS)
    return pd.read_csv(path, encoding="utf-8-sig")


def save_review(company_id: str, fiscal_year: int, decision: str, reviewer: str = "demo_user", comment: str = "", path: Path = REVIEW_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    df = load_reviews(path)
    rec = pd.DataFrame([{ "company_id": str(company_id), "fiscal_year": int(fiscal_year), "decision": decision,
                         "reviewer": reviewer or "demo_user", "comment": comment,
                         "reviewed_at_utc": datetime.now(timezone.utc).isoformat()}])
    df = pd.concat([df, rec], ignore_index=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return rec.iloc[0].to_dict()
