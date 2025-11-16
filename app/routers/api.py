from fastapi import APIRouter, UploadFile, Form
from fastapi.responses import JSONResponse
import json
from app.core.algorithm import process_operations

router = APIRouter(prefix="/api", tags=["API"])

@router.options("/process")
async def options_process():
    return JSONResponse(content={}, headers={
        "Access-Control-Allow-Origin": "http://localhost:5173",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Allow-Credentials": "true",
    })

@router.post("/process")
async def process_file(file: UploadFile, workers: str = Form(...)):
    try:
        csv_bytes = await file.read()
        workers_data = json.loads(workers)
        result = process_operations(csv_bytes, workers_data)

        response = JSONResponse({
            "success": True,
            "data": result["table"],
            "total_sum": float(result["total_sum"]),
            "max_parallel_time": float(result["max_parallel_time"]),
            "csv": result["result_csv"]
        })
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:5173"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response
    except Exception as e:
        error_response = JSONResponse(
            {"success": False, "error": str(e)},
            status_code=400
        )
        error_response.headers["Access-Control-Allow-Origin"] = "http://localhost:5173"
        return error_response