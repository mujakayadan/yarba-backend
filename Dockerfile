FROM python:3.13-slim

WORKDIR /app

# Copy everything first to ensure all files are present
COPY . .

# Install Poetry and dependencies
RUN pip install poetry==2.0.1 \
    && poetry config virtualenvs.create false \
    && poetry install --without dev \
    && ls -la

# Run the application
CMD ["python", "api.py"]
