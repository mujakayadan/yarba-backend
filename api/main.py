"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Fix middleware import
from api.middleware import setup_middlewares

# Fix imports - use explicit imports from config modules
from config.logging_config import configure_logging, get_logger
from config.settings import settings
from core.database.init import init_db

# Define API constants that were missing from config
API_V1_PREFIX = "/api/v1"
API_TAGS_METADATA = [
    {"name": "auth", "description": "Authentication operations"},
    {"name": "profiles", "description": "User profile management"},
    {"name": "resumes", "description": "Resume operations"},
    {"name": "cover-letters", "description": "Cover letter operations"},
    {"name": "portfolios", "description": "Portfolio operations"},
    {"name": "health", "description": "Application health checks"},
]

# Configure logging
configure_logging()
logger = get_logger(__name__)


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
    client = await init_db()
    if not client:
        logger.error("Failed to initialize database connection")
        raise RuntimeError("Failed to initialize database connection")
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
from api.routers import auth, cover_letters, portfolios, profiles, resumes

app.include_router(auth.router, prefix=f"{API_V1_PREFIX}/auth", tags=["auth"])
app.include_router(resumes.router, prefix=f"{API_V1_PREFIX}/resumes", tags=["resumes"])
app.include_router(
    cover_letters.router,
    prefix=f"{API_V1_PREFIX}/cover-letters",
    tags=["cover-letters"],
)
app.include_router(
    portfolios.router,
    prefix=f"{API_V1_PREFIX}/portfolios",
    tags=["portfolios"],
)
app.include_router(
    profiles.router,
    prefix=f"{API_V1_PREFIX}/profiles",
    tags=["profiles"],
)


@app.get("/", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": app.version}
