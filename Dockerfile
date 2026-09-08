# Slim base: the full python image is ~1GB, slim is ~150MB. Image size
# matters because it's what you pay to push, pull, and cold-start on every
# deploy.
FROM python:3.11-slim

WORKDIR /app

# Install dependencies BEFORE copying the source code. Docker caches each
# layer, so as long as requirements.txt hasn't changed, rebuilds skip the
# slow pip install entirely and only redo the fast COPY below. Copying the
# code first would invalidate that cache on every single code change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY api/ ./api/
COPY dashboard/ ./dashboard/
COPY models/ ./models/

# The API and the dashboard run as two separate services from this one
# image (see docker-compose.yml) — each gets its own command.
EXPOSE 8000 8501

# Fails the container health check if the model didn't load, so a broken
# deploy is caught immediately instead of silently serving errors.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
