from fastapi import APIRouter, UploadFile, Form
from fastapi.responses import JSONResponse
import json
from app.core.algorithm import process_operations

router = APIRouter(prefix="/api", tags=["API"])

@router.post("/process")
async def process_file(file: UploadFile, workers: str = Form(...)):
    try:
        csv_bytes = await file.read()
        workers_data = json.loads(workers)
        result = process_operations(csv_bytes, workers_data)

        return JSONResponse({
            "success": True,
            "data": result["table"],
            "total_sum": result["total_sum"],
            "max_parallel_time": result["max_parallel_time"],
            "csv": result["result_csv"]
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})