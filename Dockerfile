FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --shell /bin/bash appuser

COPY . .
RUN chown -R appuser:appuser /app
USER appuser

ENV SERVICE=dashboard
ENV AML_SHAP_MAX_ROWS=5000
EXPOSE 8501 8000
CMD ["bash", "docker/entrypoint.sh"]
