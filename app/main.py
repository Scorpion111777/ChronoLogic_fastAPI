from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routers import api

app = FastAPI(title="ChronoLogic")

# CORS - allow all localhost dev ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(api.router)

@app.get("/health")
def health():
    return {"status": "ok", "app": "ChronoLogic"}
