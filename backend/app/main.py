from app.api.routes import router as schemes_router
from fastapi import FastAPI, HTTPException
from app.api.profiles import router as profiles_router

from app.database.session import check_db_connection

app = FastAPI(
    title="Janvaani API",
    description="Backend API for the Janvaani NLP project",
    version="0.1.0",
)

app.include_router(schemes_router)
app.include_router(profiles_router)

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
