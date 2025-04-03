FROM python:3.13-slim

WORKDIR /app

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy poetry files first to leverage Docker cache
COPY pyproject.toml poetry.lock ./

# Install Poetry and dependencies
RUN pip install poetry==2.0.1 \
    && poetry config virtualenvs.create false \
    && poetry install --without dev

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "api.py"]
