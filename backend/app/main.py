from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings

app = FastAPI(
    title="CASE Colaborativo",
    description="Sistema de diagramas UML colaborativos con IA",
    version="0.0.1"
)

# ===== CORS =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.CORS_ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== HEALTH CHECK =====
@app.get("/health")
def health():
    return {"status": "ok", "service": "CASE Colaborativo Backend"}