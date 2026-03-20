import json
from fastapi import APIRouter, UploadFile, HTTPException, File, Form
from fastapi.responses import JSONResponse
from typing import List, Optional
from src.core.algorithm import process_fixed_operations, process_multiple_files

router = APIRouter(prefix="/api", tags=["API"])


@router.post("/process-fixed")
async def process_fixed(file: UploadFile):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")
    csv_bytes = await file.read()
    try:
        result = process_fixed_operations(csv_bytes)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return JSONResponse({"success": True, **result})


@router.post("/process-multi")
async def process_multi(
    files: List[UploadFile] = File(...),
    workers_profile: Optional[str] = Form(default="{}"),
    sample_quantity: int = Form(default=1),
    sample_quantities: Optional[str] = Form(default=None),  # JSON array of per-file quantities
):
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")

    for f in files:
        if not f.filename.endswith(".csv"):
            raise HTTPException(status_code=400, detail=f"Only CSV files are accepted: {f.filename}")

    try:
        profile = json.loads(workers_profile) if workers_profile else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="Invalid workers_profile JSON")

    # Parse per-file quantities; fall back to uniform sample_quantity
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

    # Pad/truncate to match file count
    while len(quantities_list) < len(files):
        quantities_list.append(1)
    quantities_list = [max(1, int(q)) for q in quantities_list[:len(files)]]

    files_data = []
    for f, qty in zip(files, quantities_list):
        files_data.append({"filename": f.filename, "bytes": await f.read(), "quantity": qty})

    try:
        result = process_multiple_files(files_data, profile)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return JSONResponse({"success": True, **result})
