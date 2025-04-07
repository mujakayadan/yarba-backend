"""API healthcheck file to verify folder structure."""

# This file is used to ensure the api directory is properly copied
# into the Docker image

API_PRESENT = True


def check_api_exists():
    """Return True if API directory is properly set up."""
    return API_PRESENT
