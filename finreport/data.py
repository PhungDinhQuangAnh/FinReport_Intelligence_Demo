"""Ingest and validate the original competition data, without modifying source CSVs."""
from __future__ import annotations

import hashlib
from pathlib import Path
import pandas as pd
import numpy as np
from .config import RAW, METADATA, KEY, TABLES


class DataValidationError(ValueError):
    pass


def load_sources(raw_dir: Path = RAW) -> dict[str, pd.DataFrame]:
    result = {}
    for name in ["company_info", *TABLES]:
        path = Path(raw_dir) / f"{name}.csv"
        if not path.is_file():
            raise FileNotFoundError(f"Thiếu dữ liệu BTC: {path}")
        df = pd.read_csv(path, encoding="utf-8-sig")
        if "company_id" not in df.columns:
            raise DataValidationError(f"Thiếu company_id: {name}")
        df["company_id"] = df["company_id"].astype(str)
        if name != "company_info":
            if "fiscal_year" not in df.columns:
                raise DataValidationError(f"Thiếu fiscal_year: {name}")
            df["fiscal_year"] = pd.to_numeric(df["fiscal_year"], errors="raise").astype(int)
        result[name] = df
    return result


def _numeric_equal(a: pd.Series, b: pd.Series, atol: float = 1e-6) -> pd.Series:
    return pd.Series(np.isclose(a.to_numpy(dtype=float), b.to_numpy(dtype=float), atol=atol, rtol=0), index=a.index)


def validate_sources(tables: dict[str, pd.DataFrame], metadata_dir: Path = METADATA,
                     raw_dir: Path = RAW, check_manifest: bool = True) -> dict:
    errors = []
    checks = {}
    info = tables["company_info"]
    if info["company_id"].duplicated().any():
        errors.append("company_info trùng company_id")
    if not info["data_is_synthetic"].astype(str).str.upper().eq("TRUE").all():
        errors.append("Một số doanh nghiệp không có cờ dữ liệu giả lập TRUE")
    if not info["statement_unit"].eq("VND_million").all():
        errors.append("Đơn vị dữ liệu không phải VND_million")
    keys = None
    for name in TABLES:
        tab = tables[name]
        if tab.duplicated(KEY).any():
            errors.append(f"{name}: trùng company_id + fiscal_year")
        if tab.isna().any().any():
            errors.append(f"{name}: phát hiện giá trị thiếu trong nguồn")
        unknown = set(tab.company_id) - set(info.company_id)
        if unknown:
            errors.append(f"{name}: mã doanh nghiệp không có trong company_info: {unknown}")
        k = set(zip(tab.company_id, tab.fiscal_year))
        if keys is not None and k != keys:
            errors.append(f"{name}: tập company-year không nhất quán")
        keys = k
    checks["source_row_counts"] = {k: len(v) for k, v in tables.items()}
    checks["company_year_count"] = len(keys) if keys else 0
    if check_manifest:
        manifest_path = Path(metadata_dir) / "dataset_manifest.csv"
        manifest = pd.read_csv(manifest_path, encoding="utf-8-sig")
        verified = 0
        for _, entry in manifest.iterrows():
            source = Path(raw_dir) / str(entry.file_name)
            if source.exists():
                digest = hashlib.sha256(source.read_bytes()).hexdigest()
                if digest != str(entry.sha256):
                    errors.append(f"SHA-256 không khớp: {source.name}")
                if len(tables[source.stem]) != int(entry.row_count):
                    errors.append(f"Sai số dòng trong manifest: {source.name}")
                verified += 1
        checks["manifest_files_verified"] = verified
    # Reconcile using the financial statements themselves.
    bs, cf, inc = tables["balance_sheet"], tables["cashflow"], tables["income_statement"]
    checks["balance_sheet_balanced"] = int(_numeric_equal(bs.total_assets_vnd_mn, bs.total_liabilities_vnd_mn + bs.total_equity_vnd_mn).sum())
    checks["balance_sheet_rows"] = len(bs)
    cfb = cf.merge(bs[KEY + ["cash_and_cash_equivalents_vnd_mn"]], on=KEY, validate="one_to_one")
    checks["cash_begin_plus_change_equals_end"] = int(_numeric_equal(cfb.beginning_cash_vnd_mn + cfb.net_change_in_cash_vnd_mn, cfb.ending_cash_vnd_mn).sum())
    checks["cashflow_three_parts_equals_change"] = int(_numeric_equal(cfb.net_cash_from_operating_activities_vnd_mn + cfb.net_cash_from_investing_activities_vnd_mn + cfb.net_cash_from_financing_activities_vnd_mn, cfb.net_change_in_cash_vnd_mn).sum())
    checks["ending_cash_matches_balance_sheet"] = int(_numeric_equal(cfb.ending_cash_vnd_mn, cfb.cash_and_cash_equivalents_vnd_mn).sum())
    ci = cf.merge(inc[KEY + ["net_income_vnd_mn"]], on=KEY, suffixes=("_cashflow", "_income"), validate="one_to_one")
    checks["net_income_cross_report"] = int(_numeric_equal(ci.net_income_vnd_mn_cashflow, ci.net_income_vnd_mn_income).sum())
    for label in ["balance_sheet_balanced", "cash_begin_plus_change_equals_end", "cashflow_three_parts_equals_change", "ending_cash_matches_balance_sheet", "net_income_cross_report"]:
        if checks[label] != checks["company_year_count"]:
            errors.append(f"Đối chiếu {label} không đạt ở một số bản ghi")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors, "checks": checks}


def merge_statements(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    data = tables["income_statement"].copy()
    for name in ["balance_sheet", "cashflow", "financial_notes"]:
        other = tables[name].copy()
        overlaps = (set(data.columns) & set(other.columns)) - set(KEY)
        for col in overlaps:
            # Both income statement and cash flow contain NI and D&A.
            other = other.rename(columns={col: f"{col}_{name}"})
        data = data.merge(other, how="inner", on=KEY, validate="one_to_one")
    data = data.merge(tables["company_info"], on="company_id", how="left", validate="many_to_one")
    return data.sort_values(KEY).reset_index(drop=True)


def load_validated(raw_dir: Path = RAW, metadata_dir: Path = METADATA, strict: bool = True):
    sources = load_sources(raw_dir)
    report = validate_sources(sources, metadata_dir=metadata_dir, raw_dir=raw_dir)
    if strict and report["status"] != "PASS":
        raise DataValidationError("Dữ liệu không đạt kiểm tra: " + "; ".join(report["errors"]))
    return merge_statements(sources), report
