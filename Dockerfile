FROM python:3.13-slim

WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==2.0.1

# Copy dependency files first
COPY pyproject.toml poetry.lock ./

# Pin aiohttp to a non-yanked version and install pre-built wheels when possible
RUN poetry config virtualenvs.create false \
    && pip install --no-build-isolation aiohttp==3.9.3 \
    && poetry install --only main

# Debug - Check build environment
RUN echo "Starting build..." && pwd && ls -la

# Copy the entire project
COPY . .

# Debug - Check files after copying
RUN echo "Files after copying:" && ls -la && echo "API directory:" && ls -la api

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "api.py"]
