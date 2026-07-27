import json
from fastapi import APIRouter, UploadFile, HTTPException, File, Form, Query
from fastapi.responses import JSONResponse, Response
from typing import List, Optional
from src.core.algorithm import process_fixed_operations, process_multiple_files
from src.core.xlsx_utils import read_xlsx_to_dataframe, export_to_xlsx

router = APIRouter(prefix="/api", tags=["API"])

ALLOWED_EXTENSIONS = (".csv", ".xlsx", ".xls")


def _validate_files(files: List[UploadFile]):
    for f in files:
        fn = f.filename or ""
        if not any(fn.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
            raise HTTPException(
                status_code=400,
                detail=f"Only CSV/XLSX files are accepted: {fn}",
            )


def _is_xlsx(filename: str) -> bool:
    return filename.lower().endswith((".xlsx", ".xls"))


def _process_xlsx_fixed(xlsx_bytes: bytes, filename: str) -> dict:
    from src.core.algorithm import _process_single_df
    import time as _time
    start = _time.time()
    df, meta = read_xlsx_to_dataframe(xlsx_bytes)
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
    from src.core.algorithm import _sanitize_for_json
    records = _sanitize_for_json(records)

    return {
        "total_before": total_before,
        "total_after": total_after,
        "filtered_count": total_before - total_after,
        "processing_time_sec": round(_time.time() - start, 2),
        "data": records,
        "import_meta": meta,
    }


def _process_xlsx_multi(
    files_data: List[dict],
    workers_profile: dict,
    time_unit: Optional[str] = None,
) -> dict:
    import time as _time
    from src.core.algorithm import _process_single_df, _sanitize_for_json
    import pandas as pd

    start = _time.time()
    all_dfs = []
    file_stats = []
    total_before_all = 0
    all_meta = []

    for fd in files_data:
        product_qty = max(1, int(fd.get("quantity", 1)))
        try:
            df, meta = read_xlsx_to_dataframe(fd["bytes"], time_unit=time_unit)
            all_meta.append({"filename": fd["filename"], **meta})
            before = len(df)
            total_before_all += before
            df = _process_single_df(df)
            df["_source_file"] = fd["filename"]
            df["_product_quantity"] = product_qty

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
        raise ValueError("No valid XLSX files could be processed.")

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
        "processing_time_sec": round(_time.time() - start, 4),
        "total_products": total_products,
        "files_processed": len(all_dfs),
        "file_stats": file_stats,
        "worker_summary": worker_summary,
        "data": records,
        "import_meta": all_meta,
    }


@router.post("/process-fixed")
async def process_fixed(
    file: UploadFile = File(...),
    time_unit: Optional[str] = Form(default=None),
):
    fn = file.filename or ""
    file_bytes = await file.read()

    if _is_xlsx(fn):
        try:
            result = _process_xlsx_fixed(file_bytes, fn)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
    else:
        if not fn.lower().endswith(".csv"):
            raise HTTPException(status_code=400, detail="Only CSV/XLSX files are accepted")
        try:
            result = process_fixed_operations(file_bytes)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    return JSONResponse({"success": True, **result})


@router.post("/process-multi")
async def process_multi(
    files: List[UploadFile] = File(...),
    workers_profile: Optional[str] = Form(default="{}"),
    sample_quantity: int = Form(default=1),
    sample_quantities: Optional[str] = Form(default=None),
    time_unit: Optional[str] = Form(default=None),
):
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")

    _validate_files(files)

    try:
        profile = json.loads(workers_profile) if workers_profile else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="Invalid workers_profile JSON")

    quantities_list = None
    if sample_quantities:
        try:
            quantities_list = json.loads(sample_quantities)
            if not isinstance(quantities_list, list):
                quantities_list = None
        except (json.JSONDecodeError, TypeError):
            quantities_list = None

    if quantities_list is None:
        quantities_list = [max(1, sample_quantity)] * len(files)

    while len(quantities_list) < len(files):
        quantities_list.append(1)
    quantities_list = [max(1, int(q)) for q in quantities_list[:len(files)]]

    has_xlsx = any(_is_xlsx(f.filename or "") for f in files)

    if has_xlsx:
        files_data = []
        for f, qty in zip(files, quantities_list):
            files_data.append({"filename": f.filename, "bytes": await f.read(), "quantity": qty})
        try:
            result = _process_xlsx_multi(files_data, profile, time_unit=time_unit)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
    else:
        files_data = []
        for f, qty in zip(files, quantities_list):
            files_data.append({"filename": f.filename, "bytes": await f.read(), "quantity": qty})
        try:
            result = process_multiple_files(files_data, profile)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    return JSONResponse({"success": True, **result})


@router.post("/import-xlsx")
async def import_xlsx(
    file: UploadFile = File(...),
    time_unit: Optional[str] = Form(default=None),
):
    fn = file.filename or ""
    if not _is_xlsx(fn):
        raise HTTPException(status_code=400, detail="Only XLSX files are accepted for this endpoint")

    xlsx_bytes = await file.read()

    try:
        df, meta = read_xlsx_to_dataframe(xlsx_bytes, time_unit=time_unit)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    from src.core.algorithm import _process_single_df, _sanitize_for_json
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

    return JSONResponse({
        "success": True,
        "total_before": total_before,
        "total_after": total_after,
        "filtered_count": total_before - total_after,
        "data": records,
        "import_meta": meta,
    })


@router.post("/export-xlsx")
async def export_xlsx_endpoint(
    data: str = Form(...),
):
    try:
        rows = json.loads(data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="Invalid JSON data")

    if not isinstance(rows, list) or not rows:
        raise HTTPException(status_code=422, detail="Data must be a non-empty array")

    xlsx_bytes = export_to_xlsx(rows)

    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=operations_export.xlsx"},
    )
