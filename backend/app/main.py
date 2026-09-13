from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config.settings import settings
from app.core.exceptions import AppException, ConflictError, ForbiddenError, NotFoundError, UnauthorizedError

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

# ===== EXCEPCIONES DE DOMINIO =====
_STATUS_BY_EXCEPTION = {
    ConflictError: status.HTTP_409_CONFLICT,
    UnauthorizedError: status.HTTP_401_UNAUTHORIZED,
    ForbiddenError: status.HTTP_403_FORBIDDEN,
    NotFoundError: status.HTTP_404_NOT_FOUND,
}


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    status_code = _STATUS_BY_EXCEPTION.get(type(exc), status.HTTP_400_BAD_REQUEST)
    return JSONResponse(status_code=status_code, content={"detail": exc.message})

# ===== HEALTH CHECK =====
@app.get("/health")
def health():
    return {"status": "ok", "service": "CASE Colaborativo Backend"}