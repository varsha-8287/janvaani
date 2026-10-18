
from fastapi import FastAPI, HTTPException

from app.api.routes import router
from app.database.session import check_db_connection

app = FastAPI(
    title="Janvaani NLP API",
    description="Backend API for multilingual scheme discovery and eligibility.",
    version="0.1.0",
)

app.include_router(router, prefix="/api", tags=["Eligibility"])


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health/db")
def database_health_check():
    try:
        check_db_connection()
        return {"status": "ok", "database": "connected"}
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed",
        )
