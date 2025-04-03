FROM python:3.13-slim

WORKDIR /app

# Copy poetry files first to leverage Docker cache
COPY pyproject.toml poetry.lock ./

# Install Poetry and dependencies
RUN pip install poetry==2.0.1 \
    && poetry config virtualenvs.create false \
    && poetry install --without dev

# Copy the rest of the application
COPY . .

# Set environment variables
ENV PORT=8000
ENV PYTHONPATH=/app

# Run the application
CMD ["python", "api.py"]
