
from fastapi import FastAPI, HTTPException

from app.api.profiles import router as profiles_router
from app.api.routes import router as schemes_router
from app.api.routes import eligibility_router
from app.database.session import check_db_connection

app = FastAPI(
    title="Janvaani NLP API",
    description="Backend API for multilingual scheme discovery and eligibility.",
    version="0.1.0",
)

app.include_router(schemes_router)
app.include_router(profiles_router)
app.include_router(eligibility_router)


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
