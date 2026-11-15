"""FastAPI application entry point for the Knowledge Retrieval Platform.

Exposes REST APIs for document upload, ingestion status, and health checks.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/", summary="Root Health and Service Information")
def root():
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

