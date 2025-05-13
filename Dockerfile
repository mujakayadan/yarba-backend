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

# Copy TeX Live distribution from the latex_env stage
# reitzig/texlive-minimal usually installs into /usr/local/texlive/ or similar
COPY --from=latex_env /usr/local/texlive/ /usr/local/texlive/

# Copy essential TeX Live binaries from the minimal image's TeX Live bin directory
# The exact path might be /usr/local/texlive/YYYY/bin/ARCH, but tlmgr often creates symlinks or updates PATH
# We'll assume binaries are accessible in a common path within the texlive structure or standard /usr/local/bin after tlmgr use.
# If not, these explicit copies might need adjustment after inspecting the latex_env stage.
COPY --from=latex_env /usr/local/bin/pdflatex /usr/local/bin/
COPY --from=latex_env /usr/local/bin/xelatex /usr/local/bin/
COPY --from=latex_env /usr/local/bin/lualatex /usr/local/bin/
COPY --from=latex_env /usr/local/bin/mktexlsr /usr/local/bin/
COPY --from=latex_env /usr/local/bin/fmtutil* /usr/local/bin/
COPY --from=latex_env /usr/local/bin/updmap* /usr/local/bin/
COPY --from=latex_env /usr/local/bin/kpsewhich /usr/local/bin/

# Ensure the directory for TeX Live binaries is in PATH
# This path might need adjustment based on reitzig/texlive-minimal's structure
ENV PATH=/usr/local/texlive/bin/x86_64-linux:$PATH:/usr/local/bin

# Install system dependencies for building Python packages (git, build-essential)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    git \
    ca-certificates \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# After copying TeX Live files, rebuild the TeX Live file database
RUN mktexlsr /usr/local/texlive || mktexlsr

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
