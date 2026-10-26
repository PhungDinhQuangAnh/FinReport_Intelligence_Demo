"""Audit trail utilities for deterministic pipeline runs."""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from .config import RAW, MODEL_NAME, MODEL_VERSION


def input_fingerprint() -> str:
    h = hashlib.sha256()
    for p in sorted(Path(RAW).glob("*.csv")):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def run_id() -> str:
    raw = f"{MODEL_NAME}|{MODEL_VERSION}|{input_fingerprint()}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def make_audit_log(stage_counts: dict[str, int], extra: dict | None = None) -> pd.DataFrame:
    rid = run_id()
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for order, (stage, count) in enumerate(stage_counts.items(), start=1):
        rows.append({"run_id": rid, "stage_order": order, "stage": stage, "record_count": int(count),
                     "status": "PASS", "model_name": MODEL_NAME, "model_version": MODEL_VERSION,
                     "input_fingerprint": input_fingerprint(), "generated_at_utc": now})
    if extra:
        rows.append({"run_id": rid, "stage_order": len(rows)+1, "stage": "SUMMARY", "record_count": int(extra.get("records", 0)),
                     "status": str(extra.get("status", "PASS")), "model_name": MODEL_NAME, "model_version": MODEL_VERSION,
                     "input_fingerprint": input_fingerprint(), "generated_at_utc": now})
    return pd.DataFrame(rows)


def write_jsonl(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for rec in df.to_dict("records"):
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
