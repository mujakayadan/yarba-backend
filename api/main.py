"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import API_TAGS_METADATA, API_V1_PREFIX, configure_logging, settings

from ..core.database.init import init_database
from .middleware import setup_middlewares

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan event handler.

    This runs on startup and shutdown of the application.

    Args:
        app: FastAPI application
    """
    # Startup: Initialize database connection
    logger.info("Initializing database connection")
    await init_database(
        mongodb_uri=settings.mongodb_uri,
        database_name=settings.mongodb_database,
    )
    logger.info("Application startup complete")

    yield

    # Shutdown: Clean up resources
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.api.title,
    description=settings.api.description,
    version=settings.api.version,
    openapi_url=settings.api.openapi_url,
    docs_url=settings.api.docs_url,
    redoc_url=settings.api.redoc_url,
    openapi_tags=API_TAGS_METADATA,
    lifespan=lifespan,
    debug=settings.api.debug,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=settings.api.cors_allow_credentials,
    allow_methods=settings.api.cors_allow_methods,
    allow_headers=settings.api.cors_allow_headers,
)

# Set up application middlewares
setup_middlewares(app)

# Import and include routers
from .routers import auth, cover_letters, resumes

app.include_router(auth.router, prefix=f"{API_V1_PREFIX}/auth", tags=["auth"])
app.include_router(resumes.router, prefix=f"{API_V1_PREFIX}/resumes", tags=["resumes"])
app.include_router(
    cover_letters.router,
    prefix=f"{API_V1_PREFIX}/cover-letters",
    tags=["cover-letters"],
)


@app.get("/", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": app.version}
