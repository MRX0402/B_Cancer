from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings as app_settings
from .database import Base, engine
from . import models  # noqa: F401 - ensures models are registered before create_all
from .routers import (
    auth, patients, doctors, appointments, lab_results,
    treatments, scans, alerts, trials, dashboard, chat, reports, ml,
)
from .routers import settings as settings_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="B-Cancer API",
    description="B-Cancer — Miya o'smasi tibbiy platformasi uchun backend API (frontend alohida ishlaydi)",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(doctors.router)
app.include_router(appointments.router)
app.include_router(lab_results.router)
app.include_router(treatments.router)
app.include_router(scans.router)
app.include_router(alerts.router)
app.include_router(trials.router)
app.include_router(dashboard.router)
app.include_router(chat.router)
app.include_router(settings_router.router)
app.include_router(reports.router)
app.include_router(ml.router)


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}


@app.get("/", tags=["health"])
def root():
    return {
        "service": "B-Cancer API",
        "docs": "/docs",
        "note": "Bu faqat backend (API). Frontend alohida papkada/serverda ishlaydi.",
    }
