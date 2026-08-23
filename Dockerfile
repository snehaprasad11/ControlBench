# LockBench — one container that builds the React frontend and serves it together
# with the FastAPI backend, so the whole app is a single service at one URL.

# ---- stage 1: build the React frontend ----
FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- stage 2: Python runtime (API + built frontend) ----
FROM python:3.12-slim
WORKDIR /app

# numpy/scipy/scikit-learn/control all ship wheels, so no build toolchain is needed.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# App code + data + the trained ML surrogate.
COPY controlbench/ ./controlbench/
COPY api/ ./api/
COPY data/ ./data/
COPY models/ ./models/

# The compiled frontend from stage 1 (api/main.py serves it at "/").
COPY --from=frontend /app/frontend/dist ./frontend/dist

ENV PORT=8000
EXPOSE 8000
# Shell form so ${PORT} (set by the host, e.g. Render) is expanded at runtime.
CMD uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}
