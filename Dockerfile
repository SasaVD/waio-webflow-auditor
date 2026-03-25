# Stage 1: Build Frontend
FROM node:22-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Build Backend and Final Image
FROM python:3.10-slim
WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -c "import nltk; nltk.download('punkt_tab')"

# Install Playwright and all its browser dependencies
RUN playwright install chromium
RUN playwright install-deps

# Copy backend application
COPY backend/ ./backend/

# Copy frontend static build to backend/static
COPY --from=frontend-builder /app/frontend/dist ./backend/static

# Set entrypoint
ENV PORT=8000
EXPOSE 8000
WORKDIR /app/backend
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"
