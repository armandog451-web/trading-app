FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy backend source code
COPY backend/ ./backend/

# Install dependencies (adjust if requirements.txt exists)
RUN if [ -f backend/requirements.txt ]; then pip install --no-cache-dir -r backend/requirements.txt; else pip install --no-cache-dir structlog pydantic pydantic-settings httpx; fi

# Expose optional metrics port (if Prometheus metrics are added)
EXPOSE 8001

# Default command to run the demo engine
CMD ["python", "backend/run_test_engine.py"]
