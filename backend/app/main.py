
from fastapi import FastAPI, HTTPException
from app.api.review import router as review_router

from app.api.ingestion import router as ingestion_router
from app.api.profiles import router as profiles_router
from app.api.routes import router as schemes_router
from app.api.routes import eligibility_router
from app.database.session import check_db_connection
from app.api.retrieval import router as retrieval_router
from app.api.ask import router as rag_router
from app.api.chat import router as chat_router
from app.speech.router import router as speech_router
from app.applications.router import router as applications_router
from fastapi.middleware.cors import CORSMiddleware
from app.documents.router import router as documents_router

app = FastAPI(
    title="Janvaani NLP API",
    description="Backend API for multilingual scheme discovery and eligibility.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(schemes_router)
app.include_router(profiles_router)
app.include_router(eligibility_router)
app.include_router(ingestion_router)
app.include_router(review_router)

app.include_router(retrieval_router)
app.include_router(rag_router)
app.include_router(chat_router)
app.include_router(speech_router)
app.include_router(applications_router)
app.include_router(documents_router)

@app.on_event("startup")
def on_startup():
    try:
        from app.database.base import Base
        from app.database.session import engine
        import app.database.models
        Base.metadata.create_all(bind=engine)
        print("[Startup] Database tables verified/created successfully.")
    except Exception as e:
        print("[Startup] Warning: create_all tables:", e)

    try:
        from scripts.seed_pilot_schemes import seed_schemes
        seed_schemes()
    except Exception:
        try:
            from backend.scripts.seed_pilot_schemes import seed_schemes
            seed_schemes()
        except Exception as e:
            print("[Startup] Seed schemes skipped or failed:", e)

@app.get("/version")
def version():
    return {"version": "0.2.0-bhashini-ready", "status": "deployed"}

@app.get("/seed")
def trigger_seed():
    try:
        count = 0
        try:
            from scripts.seed_pilot_schemes import seed_schemes
            count = seed_schemes()
        except Exception:
            from backend.scripts.seed_pilot_schemes import seed_schemes
            count = seed_schemes()
        return {"status": "ok", "count": count, "message": f"Successfully seeded {count} pilot schemes"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

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
