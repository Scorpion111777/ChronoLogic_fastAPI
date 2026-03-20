import pandas as pd
import numpy as np
from typing import Dict, Any, List
import io
import time


def _read_csv_any_encoding(csv_bytes: bytes) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp1251", "latin-1"):
        try:
            return pd.read_csv(io.BytesIO(csv_bytes), encoding=enc)
        except (UnicodeDecodeError, Exception):
            continue
    raise ValueError("Could not decode CSV. Please save it as UTF-8 or Windows-1251.")


def _sanitize_for_json(obj):
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
        return None
    return obj


def _process_single_df(df: pd.DataFrame) -> pd.DataFrame:
    if "Блок" not in df.columns:
        df["Блок"] = ""
    df["Блок"] = df["Блок"].fillna("").astype(str).str.strip()

    time_col = "Затрати часу, хв"
    if time_col not in df.columns:
        raise ValueError(f"CSV must contain '{time_col}' column")

    df[time_col] = (
        df[time_col].astype(str)
        .str.replace('\xa0', '', regex=False)
        .str.replace('\u00a0', '', regex=False)
        .str.replace(' ', '', regex=False)
        .str.replace(',', '.', regex=False)
    )
    df[time_col] = pd.to_numeric(df[time_col], errors="coerce").fillna(0.0).round(2)
    df = df[df[time_col] >= 0]

    if "Розряд" not in df.columns:
        raise ValueError("CSV must contain 'Розряд' column")

    df["Розряд"] = (
        df["Розряд"].astype(str)
        .str.replace('\xa0', '', regex=False)
        .str.replace(' ', '', regex=False)
        .str.replace(',', '.', regex=False)
    )
    df["Розряд"] = pd.to_numeric(df["Розряд"], errors="coerce").fillna(0).astype(int)
    df = df[df["Розряд"] >= 0]

    if "№ п/п" in df.columns:
        df["№ п/п"] = pd.to_numeric(df["№ п/п"], errors="coerce")

    if "Назва технологічної операції" in df.columns:
        df = df[
            df["Назва технологічної операції"].notna() &
            (df["Назва технологічної операції"].astype(str).str.strip() != "")
        ]

    df = df.drop_duplicates()

    sort_cols = [c for c in ["Блок", "№ п/п"] if c in df.columns]
    if sort_cols:
        df = df.sort_values(by=sort_cols, ignore_index=True)

    return df


def process_fixed_operations(csv_bytes: bytes) -> Dict[str, Any]:
    start_time = time.time()
    df = _read_csv_any_encoding(csv_bytes)
    total_before = len(df)
    df = _process_single_df(df)
    total_after = len(df)

    desired_order = [
        "Блок", "Робітник", "Розряд", "Обладнання",
        "№ п/п", "№ тех.оп.", "Назва технологічної операції",
        "Затрати часу, хв", "Технічні умови",
    ]
    existing_desired = [c for c in desired_order if c in df.columns]
    other_cols = [c for c in df.columns if c not in existing_desired]
    df = df[existing_desired + other_cols]

    records = df.where(df.notna(), other=None).to_dict(orient="records")
    records = _sanitize_for_json(records)

    return {
        "total_before": total_before,
        "total_after": total_after,
        "filtered_count": total_before - total_after,
        "processing_time_sec": round(time.time() - start_time, 2),
        "data": records,
    }


def process_multiple_files(
    files_data: List[Dict[str, Any]],
    workers_profile: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Each entry in files_data: { filename, bytes, quantity }
    quantity = how many units of this product to produce.
    Time values are multiplied by the product's quantity before combining.
    Each row also gets _product_quantity so the frontend can show per-product stats.
    """
    start_time = time.time()
    all_dfs = []
    file_stats = []
    total_before_all = 0

    for fd in files_data:
        product_qty = max(1, int(fd.get("quantity", 1)))
        try:
            df = _read_csv_any_encoding(fd["bytes"])
            before = len(df)
            total_before_all += before
            df = _process_single_df(df)
            df["_source_file"] = fd["filename"]
            df["_product_quantity"] = product_qty

            # Scale time by this product's quantity
            time_col = "Затрати часу, хв"
            if time_col in df.columns and product_qty > 1:
                df[time_col] = (df[time_col] * product_qty).round(2)

            all_dfs.append(df)
            file_stats.append({
                "filename": fd["filename"],
                "quantity": product_qty,
                "rows_before": before,
                "rows_after": len(df),
                "filtered": before - len(df),
            })
        except Exception as e:
            file_stats.append({
                "filename": fd["filename"],
                "quantity": product_qty,
                "error": str(e),
                "rows_before": 0,
                "rows_after": 0,
                "filtered": 0,
            })

    if not all_dfs:
        raise ValueError("No valid CSV files could be processed.")

    combined = pd.concat(all_dfs, ignore_index=True)
    workers = workers_profile.get("workers", [])

    def _assign_worker(row):
        rank = int(row.get("Розряд", 0))
        equipment = str(row.get("Обладнання", "")).strip().lower()
        for w in workers:
            w_rank = int(w.get("rank", 0))
            w_eq = str(w.get("equipment_type", "")).strip().lower()
            if w_rank == rank and (not equipment or not w_eq or w_eq in equipment or equipment in w_eq):
                return w.get("name", row.get("Робітник", ""))
        for w in workers:
            if int(w.get("rank", 0)) == rank:
                return w.get("name", row.get("Робітник", ""))
        return row.get("Робітник", "")

    if workers:
        combined["Робітник"] = combined.apply(_assign_worker, axis=1)

    desired_order = [
        "Блок", "Робітник", "Розряд", "Обладнання",
        "№ п/п", "№ тех.оп.", "Назва технологічної операції",
        "Затрати часу, хв", "Технічні умови", "_source_file", "_product_quantity",
    ]
    existing_desired = [c for c in desired_order if c in combined.columns]
    other_cols = [c for c in combined.columns if c not in existing_desired]
    combined = combined[existing_desired + other_cols]

    records = combined.where(combined.notna(), other=None).to_dict(orient="records")
    records = _sanitize_for_json(records)

    # Worker summary (time is already scaled)
    time_col = "Затрати часу, хв"
    worker_summary = []
    if "Робітник" in combined.columns and time_col in combined.columns:
        for worker_name, grp in combined.groupby("Робітник"):
            total_min = round(float(grp[time_col].sum()), 2)
            op_count = len(grp)
            profile = next((w for w in workers if w.get("name") == worker_name), {})
            worker_summary.append({
                "worker": worker_name,
                "rank": int(profile.get("rank", int(grp["Розряд"].iloc[0]) if "Розряд" in grp.columns else 0)),
                "equipment_type": profile.get("equipment_type", ""),
                "equipment_quantity": int(profile.get("equipment_quantity", 1)),
                "operations_count": op_count,
                "total_time_min": total_min,
                "total_time_hours": round(total_min / 60, 3),
            })

    total_products = sum(fd.get("quantity", 1) for fd in files_data)

    return {
        "total_before": total_before_all,
        "total_after": len(combined),
        "filtered_count": total_before_all - len(combined),
        "processing_time_sec": round(time.time() - start_time, 4),
        "total_products": total_products,
        "files_processed": len(all_dfs),
        "file_stats": file_stats,
        "worker_summary": worker_summary,
        "data": records,
    }
