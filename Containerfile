FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY crawlers ./crawlers
COPY cli ./cli
COPY web ./web
COPY core ./core
COPY ojhunt.py ./

ARG GIT_COMMIT_SHA
ARG BUILD_TIME

ENV GIT_COMMIT_SHA=${GIT_COMMIT_SHA}
ENV BUILD_TIME=${BUILD_TIME}
ENV UV_SYSTEM_PYTHON=1

COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["docker-entrypoint.sh"]
