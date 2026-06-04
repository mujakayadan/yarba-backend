FROM texlive/texlive:latest-small AS latex_env

# Install required LaTeX packages using tlmgr
# 'scheme-small' is already the base of texlive/texlive:small
RUN tlmgr update --self && \
    tlmgr install \
    collection-latexrecommended \
    collection-fontsrecommended \
    titlesec \
    marvosym \
    enumitem \
    hyphenat \
    fontawesome5 \
    seqsplit \
    collection-latexextra

FROM python:3.12-slim

WORKDIR /app

# Copy the entire TeX Live distribution from the latex_env stage
COPY --from=latex_env /usr/local/texlive/ /usr/local/texlive/

# Install system dependencies for building Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    git \
    ca-certificates \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# latest-small tracks the current TeX Live release (year changes annually).
# Symlink bin -> .../<year>/bin/<arch> so PATH stays stable across image updates.
RUN set -eux; \
    TEXLIVE_YEAR="$(ls -1 /usr/local/texlive | grep -E '^[0-9]{4}$' | sort -n | tail -1)"; \
    case "$(uname -m)" in \
        x86_64) TEXLIVE_ARCH=x86_64-linux ;; \
        aarch64) TEXLIVE_ARCH=aarch64-linux ;; \
        *) echo "Unsupported architecture: $(uname -m)"; exit 1 ;; \
    esac; \
    TEXLIVE_BIN_DIR="/usr/local/texlive/${TEXLIVE_YEAR}/bin/${TEXLIVE_ARCH}"; \
    test -x "${TEXLIVE_BIN_DIR}/kpsewhich"; \
    ln -sfn "${TEXLIVE_BIN_DIR}" /usr/local/texlive/bin; \
    /usr/local/texlive/bin/mktexlsr

ENV PATH=/usr/local/texlive/bin:${PATH}

# Install uv for dependency management
COPY --from=ghcr.io/astral-sh/uv:0.7 /uv /uvx /bin/

# Create log directory with correct permissions
RUN mkdir -p logs && chmod 755 logs

# Copy project definition and lock file
COPY pyproject.toml uv.lock ./

# Install production dependencies into the system Python environment
ENV UV_SYSTEM_PYTHON=1
RUN uv sync --frozen --no-dev

# Install Playwright browsers (use -m; uv does not put console scripts on PATH)
RUN python -m playwright install --with-deps

# Copy the rest of the application code
# A comprehensive .dockerignore file (updated in the previous step) is CRITICAL here.
COPY . .

# List directories to ensure they exist
# This command was failing. With a proper .dockerignore, it should be fine.
# If it still causes OOM, consider removing or simplifying it.
RUN echo "Directory structure after full copy and install:" && \
    ls -la && \
    echo "API directory contents:" && \
    ls -la api/

# Verify all dependencies are installed
RUN pip list

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
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "uvloop", "--http", "httptools", "--proxy-headers", "--forwarded-allow-ips", "*"]
