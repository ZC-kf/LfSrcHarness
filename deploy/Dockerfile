# syntax=docker/dockerfile:1.7
FROM node:24-bookworm-slim AS web-build
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PYTHON_DOWNLOADS=0 \
    LFSRC_ROOT=/opt/lfsrc \
    PATH=/opt/lfsrc/.venv/bin:$PATH
WORKDIR /opt/lfsrc
RUN groupadd --system lfsrc && useradd --system --gid lfsrc --home /opt/lfsrc lfsrc
COPY --from=ghcr.io/astral-sh/uv:0.12.3 /uv /uvx /bin/
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/
RUN uv sync --locked --no-dev --no-editable
COPY deploy/ ./deploy/
COPY plugins/ ./plugins/
COPY --from=web-build /build/web/dist ./web/dist
RUN mkdir -p /opt/lfsrc/runs /opt/lfsrc/package && chown -R lfsrc:lfsrc /opt/lfsrc
USER lfsrc
EXPOSE 8619 8621
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8619/health', timeout=3)"
CMD ["uvicorn", "lfsrc_harness.server:app", "--host", "0.0.0.0", "--port", "8619"]
