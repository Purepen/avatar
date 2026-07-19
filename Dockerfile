# Avatar — single container: builds the Vite frontend, runs the FastAPI backend.
# The /app layout mirrors the repo root so the backend's relative path
# resolution (knowledge/, frontend/dist) works unchanged.

# ---- Stage 1: frontend build ----
FROM node:22-slim AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: backend runtime ----
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock backend/.python-version backend/
RUN cd backend && uv sync --frozen --no-dev --no-install-project

COPY backend/app backend/app
COPY knowledge knowledge
COPY --from=frontend-build /build/dist frontend/dist

ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "cd backend && uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
