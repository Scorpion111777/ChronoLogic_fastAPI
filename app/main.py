from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routers import api

app = FastAPI(title="ChronoLogic")





# Routers


# CORS (optional if hosting front & back separately)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(api.router)

@app.get("/health")
def health():
    return {"status": "ok", "app": "ChronoLogic"}

