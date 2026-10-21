FROM python:3.14-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install -r requirements.txt
COPY . .
RUN useradd --uid 10001 --create-home appuser && mkdir -p /app/cloud-data && chown -R appuser:appuser /app
USER appuser
ENV DATA_DIR=/app/cloud-data DEMO_MODE=1 FACTORY_ANALYSIS_DEMO=1
ENV WORKFLOW_RESPONSE_POLICY=classified-template WORKFLOW_MODEL_PROVIDER=deepseek WORKFLOW_MODEL_NAME=deepseek-flash WORKFLOW_MODEL_BASE_URL=https://api.deepseek.com WORKFLOW_MODEL_ENABLED=1 WORKFLOW_TEMPLATE_FIRST=1
EXPOSE 10000
CMD ["python", "run_cloud.py"]
