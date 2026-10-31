import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.database import engine, Base, SessionLocal
from backend.seed import seed_database
from backend.routes import (
    auth, admin, subscriptions, invoices, billing, kpis, plans
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure tables exist and seed demo dataset
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield
    # Shutdown logic if needed

app = FastAPI(
    title="INTRINSIC",
    description="Next-Gen Subscription & Invoicing Operating System for Odoo Makeathon",
    version="2.0.0",
    lifespan=lifespan
)

# Enable permissive CORS for development and testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(subscriptions.router)
app.include_router(invoices.router)
app.include_router(billing.router)
app.include_router(kpis.router)
app.include_router(plans.router)

# Mount Static Assets
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"app": "INTRINSIC", "status": "running", "docs": "/docs"}
