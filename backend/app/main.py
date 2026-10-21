
from fastapi import FastAPI, HTTPException

from app.api.profiles import router as profiles_router
from app.api.routes import router as schemes_router
from app.api.routes import eligibility_router
from app.database.session import check_db_connection
from app.api.retrieval import router as retrieval_router
from app.api.ask import router as rag_router
from app.api.chat import router as chat_router
from app.speech.router import router as speech_router

app = FastAPI(
    title="Janvaani NLP API",
    description="Backend API for multilingual scheme discovery and eligibility.",
    version="0.1.0",
)

app.include_router(schemes_router)
app.include_router(profiles_router)
app.include_router(eligibility_router)
app.include_router(retrieval_router)
app.include_router(rag_router)
app.include_router(chat_router)
app.include_router(speech_router)

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
