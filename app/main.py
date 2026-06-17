import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base

# Models must be imported before create_all so Base.metadata is populated
from . import models  # noqa: F401
from .routers import auth, diagnosticos, reportes, planes, admin

Base.metadata.create_all(bind=engine)

app = FastAPI(title="LUMMO API", version="1.0.0")

_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")
origins = [o.strip() for o in _origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,         prefix="/api/v1")
app.include_router(diagnosticos.router, prefix="/api/v1")
app.include_router(reportes.router,     prefix="/api/v1")
app.include_router(planes.router,       prefix="/api/v1")
app.include_router(admin.router,        prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok", "service": "LUMMO API", "env": os.getenv("ENVIRONMENT", "local")}
