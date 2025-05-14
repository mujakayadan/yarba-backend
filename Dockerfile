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
    fullpage

FROM python:3.12-slim

WORKDIR /app

# Copy the entire TeX Live distribution from the latex_env stage
COPY --from=latex_env /usr/local/texlive/ /usr/local/texlive/

# Set the PATH to include the TeX Live binaries from our copied distribution
# For texlive/texlive:small (Ubuntu based, TeX Live 2024 usually)
# Adjust year and arch if the base image changes its internal structure.
ENV TEXLIVE_YEAR=2025
ENV TEXLIVE_ARCH=x86_64-linux
ENV TEXLIVE_BIN_DIR=/usr/local/texlive/${TEXLIVE_YEAR}/bin/${TEXLIVE_ARCH}
ENV PATH=${TEXLIVE_BIN_DIR}:${PATH}

# Install system dependencies for building Python packages (git, build-essential)
# and tools for debugging (file, elfutils for readelf)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    git \
    ca-certificates \
    file \
    elfutils \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Verify TeX Live executables and run mktexlsr
RUN echo "PATH is $PATH" && \
    echo "--- Checking TeX Live executables in ${TEXLIVE_BIN_DIR} ---" && \
    ls -la "${TEXLIVE_BIN_DIR}/mktexlsr" "${TEXLIVE_BIN_DIR}/kpsewhich" && \
    echo "--- file info for mktexlsr ---" && \
    file "${TEXLIVE_BIN_DIR}/mktexlsr" && \
    echo "--- file info for kpsewhich ---" && \
    file "${TEXLIVE_BIN_DIR}/kpsewhich" && \
    echo "--- readelf -d for kpsewhich (shows dynamic dependencies) ---" && \
    (readelf -d "${TEXLIVE_BIN_DIR}/kpsewhich" || echo "readelf failed for kpsewhich, or not an ELF file. Exit code: $?") && \
    echo "--- Trying to run kpsewhich --version directly ---" && \
    ("${TEXLIVE_BIN_DIR}/kpsewhich" --version || echo "kpsewhich --version call failed. Exit code: $?") && \
    echo "--- Trying to run mktexlsr ---" && \
    (mktexlsr || echo "mktexlsr call failed. Exit code: $?")
# RUN updmap-sys # If needed later for fonts

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

# Generate fresh lock file and install dependencies
RUN poetry config virtualenvs.create false && \
    poetry lock && \
    poetry install --only main --no-interaction --no-root

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
CMD ["python", "api.py"]
