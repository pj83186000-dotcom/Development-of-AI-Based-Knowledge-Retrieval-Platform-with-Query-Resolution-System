"""FastAPI application entry point for the Knowledge Retrieval Platform.

Exposes REST APIs for document upload, ingestion status, health checks,
and serves the Milestone 1 Interactive Web Dashboard.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.upload import router as upload_router
from backend.app.api.retrieve import router as retrieve_router
from backend.app.database.connection import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on application startup
    init_db()
    yield


app = FastAPI(
    title="AI-Based Knowledge Retrieval Platform - Ingestion API",
    description="Knowledge base ingestion pipeline for Milestone 1.3 supporting PDF, DOCX, TXT, and CSV formats.",
    version="1.3.0",
    lifespan=lifespan,
)

# Enable CORS for local development and future web client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(upload_router)
app.include_router(retrieve_router)

# Mount documentation directory for PDF downloads
doc_dir = Path("documentation")
if doc_dir.exists():
    app.mount("/documentation", StaticFiles(directory=str(doc_dir)), name="documentation")


def root():
    """Service metadata dictionary, also called directly by test suites."""
    return {
        "status": "online",
        "milestone": "Milestone 1 - Ingestion & RAG Retrieval",
        "supported_formats": ["pdf", "docx", "txt", "csv"],
        "endpoints": {
            "upload": "POST /api/documents/upload",
            "status": "GET /api/documents/status/{document_id}",
            "list": "GET /api/documents/list",
            "retrieve": "POST /api/query/retrieve",
            "evaluate": "POST /api/query/evaluate",
            "docs": "GET /docs",
        },
    }


@app.get("/", summary="Milestone 1 Interactive Web Dashboard")
def get_root_or_dashboard(request: Request):
    """Serve the Milestone 1 Dashboard to web browsers, or JSON health status to API clients."""
    accept = request.headers.get("accept", "")
    if "application/json" in accept and "text/html" not in accept:
        return JSONResponse(root())
    
    index_file = Path("frontend/index.html")
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse(root())


@app.get("/api/health", summary="Root Health and Service Information")
def health():
    return root()
