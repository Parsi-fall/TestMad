from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schema and seed demo event if needed
    try:
        await init_db()
    except Exception as e:
        print(f"[Lifespan] DB initialization error: {e}")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Service for event registration, waitlist, ticket issuance, and check-in.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.v1.events import router as events_router
from app.api.v1.registrations import router as registrations_router
from app.api.v1.checkin import router as checkin_router
from app.api.v1.ws import router as ws_router

app.include_router(events_router, prefix="/api/v1")
app.include_router(registrations_router, prefix="/api/v1")
app.include_router(checkin_router, prefix="/api/v1")
app.include_router(ws_router, prefix="/api/v1")


@app.get("/api/v1/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
