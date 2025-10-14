FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install runtime dependencies directly (container build simplicity)
# Project uses `pyproject.toml` + uv for local dev, but image installs runtime deps via pip
COPY pyproject.toml ./pyproject.toml
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --no-build-isolation -r pyproject.toml

# Copy application code
COPY app.py /app/app.py

# Expose the Flask port
EXPOSE 9000

# Read env from container env vars; .env can be provided via compose env_file
CMD ["python", "/app/app.py"]
