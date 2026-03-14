import pandas as pd
import numpy as np
from typing import Dict, Any
import io
import time


def _read_csv_any_encoding(csv_bytes: bytes) -> pd.DataFrame:
    """Try multiple encodings common for Ukrainian/Windows CSV files."""
    for enc in ("utf-8-sig", "utf-8", "cp1251", "latin-1"):
        try:
            return pd.read_csv(io.BytesIO(csv_bytes), encoding=enc)
        except (UnicodeDecodeError, Exception):
            continue
    raise ValueError("Could not decode CSV. Please save it as UTF-8 or Windows-1251.")


def _sanitize_for_json(obj):
    """Recursively replace NaN/Inf floats with None so json.dumps never crashes."""
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
        return None
    return obj


def process_fixed_operations(csv_bytes: bytes) -> Dict[str, Any]:
    start_time = time.time()

    # === READ CSV (try multiple encodings) ===
    df = _read_csv_any_encoding(csv_bytes)

    total_before = len(df)

    # === REQUIRED COLUMNS ===
    required_cols = ["Затрати часу, хв", "Розряд"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"CSV must contain '{col}' column")

    # Add Блок column if missing (treat as empty)
    if "Блок" not in df.columns:
        df["Блок"] = ""

    # === CLEAN DATA ===

    # Блок: string, strip whitespace, replace NaN with empty string
    df["Блок"] = df["Блок"].fillna("").astype(str).str.strip()

    # Time
    time_col = "Затрати часу, хв"
    df[time_col] = (
        df[time_col]
        .astype(str)
        .str.replace('\xa0', '', regex=False)
        .str.replace('\u00a0', '', regex=False)
        .str.replace(' ', '', regex=False)
        .str.replace(',', '.', regex=False)
    )
    df[time_col] = pd.to_numeric(df[time_col], errors="coerce").fillna(0.0).round(2)
    df = df[df[time_col] >= 0]

    # Rank
    df["Розряд"] = (
        df["Розряд"]
        .astype(str)
        .str.replace('\xa0', '', regex=False)
        .str.replace(' ', '', regex=False)
        .str.replace(',', '.', regex=False)
    )
    df["Розряд"] = pd.to_numeric(df["Розряд"], errors="coerce").fillna(0).astype(int)
    df = df[df["Розряд"] >= 0]

    # № п/п
    if "№ п/п" in df.columns:
        df["№ п/п"] = pd.to_numeric(df["№ п/п"], errors="coerce")

    # Drop rows with empty operation name
    if "Назва технологічної операції" in df.columns:
        df = df[
            df["Назва технологічної операції"].notna() &
            (df["Назва технологічної операції"].astype(str).str.strip() != "")
        ]

    # Drop full duplicates
    df = df.drop_duplicates()

    # Sort: Блок first, then № п/п
    sort_cols = [c for c in ["Блок", "№ п/п"] if c in df.columns]
    if sort_cols:
        df = df.sort_values(by=sort_cols, ignore_index=True)

    # Reorder columns to desired structure
    desired_order = [
        "Блок",
        "Робітник",
        "Розряд",
        "Обладнання",
        "№ п/п",
        "№ тех.оп.",
        "Назва технологічної операції",
        "Затрати часу, хв",
        "Технічні умови",
    ]
    existing_desired = [c for c in desired_order if c in df.columns]
    other_cols = [c for c in df.columns if c not in existing_desired]
    df = df[existing_desired + other_cols]

    # === SAFE JSON SERIALIZATION ===
    # Convert all remaining NaN/None to None properly
    records = df.where(df.notna(), other=None).to_dict(orient="records")
    records = _sanitize_for_json(records)

    total_after = len(df)
    processing_time_sec = round(time.time() - start_time, 2)

    return {
        "total_before": total_before,
        "total_after": total_after,
        "filtered_count": total_before - total_after,
        "processing_time_sec": processing_time_sec,
        "data": records,
    }
