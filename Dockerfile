FROM python:3.13-slim

WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry and required Python dependencies
RUN pip install --no-cache-dir poetry==2.0.1 setuptools wheel

# Create log directory with correct permissions
RUN mkdir -p logs && chmod 755 logs

# Copy the entire project first
COPY . .

# List directories to ensure they exist
RUN echo "Directory structure before installation:" && \
    ls -la && \
    echo "API directory contents:" && \
    ls -la api/

# Install dependencies with --no-root to avoid installing the project itself
RUN poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction --no-root

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHON_PATH=/app
ENV PORT=8000
ENV LOG_LEVEL=INFO

# Debug final structure
RUN echo "Final directory structure:" && \
    ls -la

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "api.py"]
