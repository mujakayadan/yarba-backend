# App image: copies source on top of the pre-built base (TeXLive + deps + Playwright).
# Rebuild the base when pyproject.toml, uv.lock, or Dockerfile.base changes.
#
# Local build (no registry):
#   docker build -f Dockerfile.base -t yarba-base .
#   docker build --build-arg BASE_IMAGE=yarba-base -t yarba-backend .
#
# DigitalOcean pulls the published base from GHCR (public package, or add GHCR credentials in App settings).

ARG BASE_IMAGE=ghcr.io/mujakayadan/yarba-backend-base:latest
FROM ${BASE_IMAGE}

WORKDIR /app

COPY . .

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "uvloop", "--http", "httptools", "--proxy-headers", "--forwarded-allow-ips", "*"]
