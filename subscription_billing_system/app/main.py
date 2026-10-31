from contextlib import asynccontextmanager
import os
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.database import engine, Base, SessionLocal
from app.seed_data import seed_database
from app.routers import auth, plans, products, discounts, subscriptions, invoices, dashboard

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables and seed data
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield

app = FastAPI(
    title="INTRINSIC - Subscription & Invoicing Management System",
    description="Production-ready enterprise subscription billing and lifecycle platform with role-based access control.",
    version="2.0.0",
    lifespan=lifespan
)

# Custom Human-Friendly Error Handling for Request Validation
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Transforms Pydantic's technical validation array into clear, polite, human-readable error messages.
    """
    error_items = []
    for err in exc.errors():
        raw_loc = err.get("loc", [])
        field_tokens = [str(token) for token in raw_loc if token not in ("body", "query", "path")]
        field_name = " ".join(field_tokens).replace("_", " ").title() if field_tokens else "Field"
        message = err.get("msg", "Invalid value entered")
        
        # Clean up technical validator labels
        if "value is not a valid" in message.lower():
            message = "is not formatted correctly"
        elif "field required" in message.lower() or "missing" in message.lower():
            message = "is required and cannot be empty"
        elif "string should have at least" in message.lower():
            message = message.replace("String should have at least", "must be at least")

        error_items.append(f"{field_name} {message}".strip())

    clean_summary = "; ".join(error_items) if error_items else "Please verify the information entered in the form."
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT if hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT") else 422,
        content={
            "detail": clean_summary,
            "user_friendly": True
        }
    )

# Enable CORS for seamless client integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router)
app.include_router(plans.router)
app.include_router(products.router)
app.include_router(discounts.router)
app.include_router(subscriptions.router)
app.include_router(invoices.router)
app.include_router(dashboard.router)

# Static and UI routes
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", include_in_schema=False)
def serve_index():
    index_file = os.path.join(TEMPLATES_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "INTRINSIC API is running. Navigate to /docs for interactive API specifications."}

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "INTRINSIC Subscription & Invoicing Engine",
        "version": "2.0.0"
    }
