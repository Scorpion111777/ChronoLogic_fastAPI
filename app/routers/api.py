import os
import time

from fastapi import APIRouter, UploadFile, Form
from fastapi.responses import JSONResponse
import json
from core.algorithm import  process_fixed_operations
import math

router = APIRouter(prefix="/api", tags=["API"])

@router.options("/process")
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