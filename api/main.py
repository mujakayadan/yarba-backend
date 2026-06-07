"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

# Load environment variables before importing any application modules
from dotenv import load_dotenv

# Explicitly load .env.local first, then fall back to .env
env_local_path = Path().absolute() / ".env.local"
env_path = Path().absolute() / ".env"

if env_local_path.exists():
    load_dotenv(dotenv_path=env_local_path)
    print(f"Loaded environment variables from {env_local_path}")
elif env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"Loaded environment variables from {env_path}")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Fix middleware import
from api.middleware import setup_middlewares

# Fix imports - use explicit imports from config modules
from config.logging_config import configure_logging, get_logger
from config.settings import settings
from core.auth.firebase import FirebaseAuth
from core.database.init import init_db

# Storage directory setup - only needed for local storage
if settings.storage.provider.lower() == "local":
    profile_pictures_dir = (
        settings.paths.base_dir
        / settings.storage.local_storage_path
        / settings.storage.profile_pictures_path
    )
    profile_pictures_dir.mkdir(parents=True, exist_ok=True)

# Define API constants that were missing from config
API_V1_PREFIX = "/api/v1"
API_TAGS_METADATA = [
    {"name": "auth", "description": "Authentication operations"},
    {"name": "profiles", "description": "User profile management"},
    {"name": "resumes", "description": "Resume operations"},
    {"name": "cover-letters", "description": "Cover letter operations"},
    {"name": "portfolios", "description": "Portfolio operations"},
    {
        "name": "portfolio-websites",
        "description": "Portfolio website deployment and management",
    },
    {
        "name": "public-portfolio",
        "description": "Public portfolio content for external sites",
    },
    {"name": "linkedin", "description": "LinkedIn integration and job application"},
    {"name": "health", "description": "Application health checks"},
    {"name": "jobs", "description": "Job related operations"},
    {"name": "webhooks", "description": "Inbound email webhooks"},
]

# Configure logging
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """FastAPI lifespan event handler.

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

    # Initialize Firebase
    logger.info("Initializing Firebase Authentication")
    firebase_initialized = FirebaseAuth.initialize()
    if not firebase_initialized:
        logger.warning("Failed to initialize Firebase. Authentication may be limited.")

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

# Set up application middlewares (error handler, logging, rate limit)
setup_middlewares(app)

# CORS must be outermost so error-handler JSON responses include CORS headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=settings.api.cors_allow_credentials,
    allow_methods=settings.api.cors_allow_methods,
    allow_headers=settings.api.cors_allow_headers,
)

# Mount static files for profile pictures if using local storage
if settings.storage.provider.lower() == "local":
    app.mount(
        f"/static/{settings.storage.profile_pictures_path}",
        StaticFiles(directory=str(profile_pictures_dir)),
        name="profile_pictures",
    )

# Import and include routers
from api.routers import (
    auth,
    cover_letters,
    job_router,
    portfolio_websites,
    portfolios,
    profiles,
    public_portfolio,
    resumes,
    webhooks,
)

# from api.routers import linkedin

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
    portfolio_websites.router,
    prefix=f"{API_V1_PREFIX}",
    tags=["portfolio-websites"],
)
app.include_router(
    public_portfolio.router,
    prefix=f"{API_V1_PREFIX}",
    tags=["public-portfolio"],
)
app.include_router(
    profiles.router,
    prefix=f"{API_V1_PREFIX}/profiles",
    tags=["profiles"],
)
app.include_router(job_router.router, prefix=f"{API_V1_PREFIX}/jobs", tags=["jobs"])
app.include_router(
    webhooks.router,
    prefix=f"{API_V1_PREFIX}/webhooks",
    tags=["webhooks"],
)
# app.include_router(
#     linkedin.router,
#     prefix=f"{API_V1_PREFIX}/linkedin",
#     tags=["linkedin"],
# )


@app.get("/", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": app.version}
