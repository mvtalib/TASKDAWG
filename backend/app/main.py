"""TASKDAWG API entry point.

Run from the backend/ folder:
    uvicorn app.main:app --reload
Interactive docs are then at http://127.0.0.1:8000/docs
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .routers import auth, contact, tasks


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="TASKDAWG API", version="0.1.0", lifespan=lifespan)

# Authentication uses a bearer token in the Authorization header, not cookies,
# so credentials are not needed for cross-origin requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(contact.router)


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok"}
