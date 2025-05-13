FROM reitzig/texlive-minimal:latest AS latex_env

# Install required LaTeX packages using tlmgr
RUN tlmgr update --self && \
    tlmgr install \
    scheme-small \
    # Collections should cover many common packages like graphicx, geometry, hyperref, common fonts (incl. lmodern), etc.
    collection-latexrecommended \
    collection-fontsrecommended \
    # Specific packages that might not be in the above or are critical
    titlesec \
    marvosym \
    xcolor \
    enumitem \
    babel-english \
    hyphenat \
    fontawesome5 \
    seqsplit
    # lmodern should be covered by collection-fontsrecommended

FROM python:3.12-slim

WORKDIR /app

# Copy the entire TeX Live distribution from the latex_env stage
COPY --from=latex_env /usr/local/texlive/ /usr/local/texlive/

# Set the PATH to include the TeX Live binaries from our copied distribution
# Note: The year (2025) and architecture (x86_64-linuxmusl) are based on previous logs.
# This might need adjustment if the reitzig/texlive-minimal image changes its internal structure.
ENV TEXLIVE_YEAR=2025
ENV TEXLIVE_ARCH=x86_64-linuxmusl
ENV TEXLIVE_BIN_DIR=/usr/local/texlive/${TEXLIVE_YEAR}/bin/${TEXLIVE_ARCH}
ENV PATH=${TEXLIVE_BIN_DIR}:$PATH

# Install system dependencies for building Python packages (git, build-essential)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    git \
    ca-certificates \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Verify that mktexlsr is found in the new PATH and that the TeX Live directory exists
RUN which mktexlsr && ls -ld /usr/local/texlive && mktexlsr
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
