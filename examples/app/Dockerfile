FROM python:3.13-slim

# Install fastapi-cloudflow from local package sources (only what's needed)
WORKDIR /opt/fastapi-cloudflow
COPY pyproject.toml ./
COPY README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

# Set up the application directory with only the app code
WORKDIR /app
COPY examples/app/ .

# Install application dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Ensure the app root is on Python import path for CLI/tools and make Python friendlier in containers
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Expose port (Cloud Run will override this with PORT env var)
EXPOSE 8080

# Run the application using PORT environment variable (Cloud Run standard)
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
