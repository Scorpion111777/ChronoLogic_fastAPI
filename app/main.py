from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import  api

app = FastAPI(title="ChronoLogic")

# CORS (optional if hosting front & back separately)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Routers

app.include_router(api.router)

@app.get("/health")
def health():
    return {"status": "ok", "app": "ChronoLogic"}

