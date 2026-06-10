from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, SessionLocal, Base
from .routers import auth, diagnosticos, reportes, planes, admin

Base.metadata.create_all(bind=engine)

app = FastAPI(title="LUMMO API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,         prefix="/api/v1")
app.include_router(diagnosticos.router, prefix="/api/v1")
app.include_router(reportes.router,     prefix="/api/v1")
app.include_router(planes.router,       prefix="/api/v1")
app.include_router(admin.router,        prefix="/api/v1")


@app.on_event("startup")
def on_startup():
    from .seed import run_seed
    db = SessionLocal()
    try:
        run_seed(db)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok", "service": "LUMMO API"}
