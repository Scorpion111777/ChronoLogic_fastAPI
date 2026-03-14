from fastapi import APIRouter, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from src.core.algorithm import process_fixed_operations

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

    return JSONResponse({
        "success": True,
        **result,
    })
