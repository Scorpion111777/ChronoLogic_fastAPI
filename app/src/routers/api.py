from fastapi import APIRouter, UploadFile
from fastapi.responses import JSONResponse
from src.core.algorithm import  process_fixed_operations

router = APIRouter(prefix="/api", tags=["API"])

@router.options("/configuration")
async def options_process():
    return JSONResponse(content={}, headers={
        "Access-Control-Allow-Origin": "http://localhost:5173",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Allow-Credentials": "true",
    })


@router.post("/process-fixed")
async def process_fixed(file: UploadFile):
    csv_bytes = await file.read()
    result = process_fixed_operations(csv_bytes)  # тепер приймає bytes

    return JSONResponse({
        "success": True,
        **result,
        "headers": {
            "Access-Control-Allow-Origin": "http://localhost:5173",
            "Access-Control-Allow-Credentials": "true"
        }
    })