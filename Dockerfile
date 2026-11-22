# Single-container image for Google Cloud Run: FastAPI serves the API, the voice WebSocket
# (/api/v1/voice/live) and the built React SPA from one origin (no CORS / mixed-content issues).

# ---- 1. Build the React frontend
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npx vite build

# ---- 2. Python backend
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=web /web/dist /app/frontend/dist
EXPOSE 8080
# Cloud Run injects $PORT; WebSockets are supported natively (set --timeout 3600 for long counter sessions)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
