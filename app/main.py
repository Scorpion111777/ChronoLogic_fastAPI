from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from app.routers import web, api
from app.core.config import settings

app = FastAPI(title="ChronoLogic")

# CORS (optional if hosting front & back separately)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")
templates = Jinja2Templates(directory=settings.TEMPLATES_DIR)

# Routers
app.include_router(web.router)
app.include_router(api.router)

@app.get("/health")
def health():
    return {"status": "ok", "app": "ChronoLogic"}