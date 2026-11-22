"""FastAPI application entry point."""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  (registers tables on Base.metadata)
from app.config import get_settings
from app.database import Base, engine
from app.routers import (
    activity,
    appointments,
    auth,
    care_recipients,
    dashboard,
    members,
    prescriptions,
    reports,
    tasks,
    timeline,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Startup: create tables if they do not exist (replaces the deprecated on_event hook)."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Care Circle API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api"
for router in (
    auth.router,
    care_recipients.router,
    members.router,
    appointments.router,
    prescriptions.router,
    reports.router,
    tasks.router,
    timeline.router,
    dashboard.router,
    activity.router,
):
    app.include_router(router, prefix=API_PREFIX)


@app.get(f"{API_PREFIX}/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
