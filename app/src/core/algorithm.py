import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
import io
import time
import base64
import re

from src.utils.llm_utils import ensure_template_columns


def _read_csv_any_encoding(csv_bytes: bytes) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp1251", "latin-1"):
        try:
            df = pd.read_csv(io.BytesIO(csv_bytes), encoding=enc)
            # If row 0 was a title header with <= 2 columns while subsequent row has more columns
            if len(df.columns) <= 2 and len(df) > 0:
                first_row = df.iloc[0].values
                non_empty = sum(1 for v in first_row if pd.notna(v) and str(v).strip())
                if non_empty > len(df.columns):
                    df_retry = pd.read_csv(io.BytesIO(csv_bytes), encoding=enc, header=1)
                    if len(df_retry.columns) > len(df.columns):
                        df = df_retry
            return df
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


def process_fixed_operations(csv_bytes: bytes, time_unit: Optional[str] = None) -> Dict[str, Any]:
    start_time = time.time()
    df = _read_csv_any_encoding(csv_bytes)
    total_before = len(df)

    df, norm_meta = ensure_template_columns(df, time_unit=time_unit)
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

    result: Dict[str, Any] = {
        "total_before": total_before,
        "total_after": total_after,
        "filtered_count": total_before - total_after,
        "processing_time_sec": round(time.time() - start_time, 2),
        "data": records,
        "import_meta": norm_meta,
    }

    result["used_llm"] = norm_meta.get("used_llm", False)
    result["column_mapping"] = norm_meta.get("column_mapping", {})
    result["input_to_template"] = norm_meta.get("input_to_template", {})
    result["original_headers"] = norm_meta.get("original_headers", [])
    if norm_meta.get("used_llm"):
        csv_text = df.where(df.notna(), other=None).to_csv(index=False, encoding="utf-8-sig")
        result["normalized_csv"] = base64.b64encode(csv_text.encode("utf-8-sig")).decode("ascii")

    return result


def process_multiple_files(
    files_data: List[Dict[str, Any]],
    workers_profile: Dict[str, Any],
    time_unit: Optional[str] = None,
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
            df, file_norm_meta = ensure_template_columns(df, time_unit=time_unit)
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
                "used_llm": file_norm_meta.get("used_llm", False),
                "column_mapping": file_norm_meta.get("column_mapping", {}),
                "input_to_template": file_norm_meta.get("input_to_template", {}),
                "original_headers": file_norm_meta.get("original_headers", []),
                "import_meta": file_norm_meta,
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

    equipment_mismatches = []
    unmatched_equipment_summary = []

    if workers:
        combined, equipment_mismatches, unmatched_equipment_summary = assign_tasks_to_workers(
            combined, workers
        )

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
                "equipment_types": profile.get("equipment_types", extract_equipment_list(profile)),
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
        "equipment_mismatches": equipment_mismatches,
        "unmatched_equipment_summary": unmatched_equipment_summary,
        "data": records,
    }


def normalize_equipment_token(val: Any) -> str:
    """
    Normalize equipment string by removing quotes, non-breaking spaces,
    collapsing whitespace, normalizing dashes and lowercasing.
    """
    if val is None:
        return ""
    s = str(val).strip()
    s = s.replace('\xa0', ' ').replace('\u00a0', ' ').replace('\t', ' ')
    s = re.sub(r'[\"\'«»“”„’`]', '', s)
    s = re.sub(r'[–—−]', '-', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip().lower()


def extract_equipment_list(worker: dict) -> List[str]:
    """
    Extract normalized list of equipment types a worker can operate.
    Supports worker['equipment_types'] (list) and worker['equipment_type'] (comma/slash string).
    """
    eq_list: List[str] = []
    raw_types = worker.get("equipment_types")
    if isinstance(raw_types, list):
        for item in raw_types:
            norm = normalize_equipment_token(item)
            if norm and norm not in eq_list:
                eq_list.append(norm)

    eq_str = str(worker.get("equipment_type", "") or "")
    if eq_str:
        for part in re.split(r'[,;/|\n]', eq_str):
            norm = normalize_equipment_token(part)
            if norm and norm not in eq_list:
                eq_list.append(norm)

    return eq_list


def is_equipment_match(required_equipment: str, worker_equipment_list: List[str]) -> bool:
    """
    Check if required equipment from file matches any of the worker's equipment types.
    Handles quotes, spacing, sub-strings, and word variations.
    """
    norm_req = normalize_equipment_token(required_equipment)
    if not norm_req or norm_req in ("-", "—", "немає", "none", "null"):
        return True

    if not worker_equipment_list:
        return True

    for w_eq in worker_equipment_list:
        if not w_eq:
            continue
        if norm_req == w_eq:
            return True
        if norm_req in w_eq or w_eq in norm_req:
            return True
        req_words = set(re.findall(r'\w+', norm_req))
        w_words = set(re.findall(r'\w+', w_eq))
        if w_words and (w_words.issubset(req_words) or req_words.issubset(w_words)):
            return True

    return False


def assign_tasks_to_workers(
    df: pd.DataFrame,
    workers: List[dict],
) -> Tuple[pd.DataFrame, List[dict], List[dict]]:
    """
    Distribute operations across workers with:
    1. Support for multiple equipment types per worker
    2. Robust equipment normalization (quotes, spaces, dashes, case)
    3. Workload balancing (minimizing accumulated assigned minutes)
    4. Detection and detailed reporting of equipment mismatches.

    Returns: (df, equipment_mismatches, unmatched_summary)
    """
    if not workers:
        return df, [], []

    worker_specs = []
    worker_workloads: Dict[str, float] = {}

    for w in workers:
        name = str(w.get("name", "")).strip()
        if not name:
            continue
        rank = int(w.get("rank", 0))
        eq_list = extract_equipment_list(w)
        qty = max(1, int(w.get("equipment_quantity", 1)))
        team = str(w.get("team", "") or w.get("teamId", "")).strip()

        worker_specs.append({
            "name": name,
            "rank": rank,
            "equipment_list": eq_list,
            "quantity": qty,
            "team": team,
            "raw": w,
        })
        worker_workloads[name] = 0.0

    if not worker_specs:
        return df, [], []

    assigned_workers = []
    equipment_mismatches = []
    mismatch_counts: Dict[str, int] = {}
    time_col = "Затрати часу, хв"

    for idx, row in df.iterrows():
        rank = int(row.get("Розряд", 0))
        raw_equipment = str(row.get("Обладнання", "") or "").strip()
        norm_equipment = normalize_equipment_token(raw_equipment)
        op_time = 0.0
        try:
            op_time = float(row.get(time_col, 0) or 0)
        except (ValueError, TypeError):
            pass

        # 1. Exact candidates: matching rank AND equipment
        exact_candidates = [
            w for w in worker_specs
            if w["rank"] == rank and is_equipment_match(raw_equipment, w["equipment_list"])
        ]

        if exact_candidates:
            chosen = min(
                exact_candidates,
                key=lambda w: worker_workloads[w["name"]] / w["quantity"]
            )
            assigned_name = chosen["name"]
            worker_workloads[assigned_name] += op_time
            assigned_workers.append(assigned_name)
            continue

        # 2. Check if equipment is available among any worker in the profile
        has_any_equipment_match = any(
            is_equipment_match(raw_equipment, w["equipment_list"])
            for w in worker_specs
        )

        # 3. Fallback candidates by rank only
        rank_candidates = [w for w in worker_specs if w["rank"] == rank]

        assigned_name = row.get("Робітник", "")
        mismatch_reason = ""

        if not has_any_equipment_match and norm_equipment and norm_equipment not in ("-", "—", "немає"):
            mismatch_reason = f"Не знайдено робітника з типом обладнання '{raw_equipment}'"
            mismatch_counts[raw_equipment] = mismatch_counts.get(raw_equipment, 0) + 1
            if rank_candidates:
                chosen = min(
                    rank_candidates,
                    key=lambda w: worker_workloads[w["name"]] / w["quantity"]
                )
                assigned_name = chosen["name"]
                worker_workloads[assigned_name] += op_time
        elif rank_candidates:
            mismatch_reason = f"Обладнання '{raw_equipment}' є в наявності, але відсутній робітник з {rank}-м розрядом"
            mismatch_counts[raw_equipment] = mismatch_counts.get(raw_equipment, 0) + 1
            chosen = min(
                rank_candidates,
                key=lambda w: worker_workloads[w["name"]] / w["quantity"]
            )
            assigned_name = chosen["name"]
            worker_workloads[assigned_name] += op_time
        else:
            if norm_equipment and norm_equipment not in ("-", "—", "немає"):
                mismatch_reason = f"Відсутній робітник як за розрядом ({rank}), так і за обладнанням '{raw_equipment}'"
                mismatch_counts[raw_equipment] = mismatch_counts.get(raw_equipment, 0) + 1

        if mismatch_reason:
            equipment_mismatches.append({
                "row_index": idx + 1,
                "tech_num": str(row.get("№ тех.оп.", "") or ""),
                "operation": str(row.get("Назва технологічної операції", "") or ""),
                "rank": rank,
                "equipment_in_file": raw_equipment,
                "assigned_worker": assigned_name,
                "reason": mismatch_reason,
            })

        assigned_workers.append(assigned_name)

    df["Робітник"] = assigned_workers

    unmatched_summary = [
        {"equipment": eq, "affected_operations": count}
        for eq, count in mismatch_counts.items()
    ]

    return df, equipment_mismatches, unmatched_summary

