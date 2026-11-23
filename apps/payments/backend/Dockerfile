# syntax=docker/dockerfile:1
# Payments backend: ONE image, three processes (ADR-0003). The start command picks the role:
#   API (default):  uvicorn northstar_payments.api.main:app ...
#   dispatcher:     python -m northstar_payments.dispatcher
#   worker:         python -m northstar_payments.worker
#   migrations:     alembic upgrade head
# Build from apps/payments/backend:  docker build -t northstar-payments-backend:local .

# ---------- Stage 1: builder (has uv; installs dependencies into /app/.venv) ----------
FROM python:3.12-slim-bookworm AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never UV_NO_CACHE=1
WORKDIR /app

# Dependencies first (changes rarely -> this layer is reused from cache on most builds).
# No BuildKit-only features (e.g. RUN --mount), so it also builds with ACR Tasks' classic builder.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Then our own code (changes often -> only this cheap layer is rebuilt).
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

# ---------- Stage 2: runtime (no uv, no compilers, no tests: only what's needed to run) ----------
FROM python:3.12-slim-bookworm AS runtime

# Microsoft ODBC Driver 18 (how Python talks to SQL Server). Installing it means accepting its licence (ACCEPT_EULA).
# https://learn.microsoft.com/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && curl -fsSL -o /tmp/packages-microsoft-prod.deb https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb \
 && dpkg -i /tmp/packages-microsoft-prod.deb && rm /tmp/packages-microsoft-prod.deb \
 && apt-get update \
 && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 unixodbc \
 && apt-get purge -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# Never run as root: a compromised process gets as few rights as possible.
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY alembic.ini ./
COPY migrations ./migrations
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1

USER 10001
EXPOSE 8000
# No HEALTHCHECK here: the same image runs the worker (no web port). Kubernetes probes and
# Compose healthchecks are defined per container instead.
CMD ["uvicorn", "northstar_payments.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
