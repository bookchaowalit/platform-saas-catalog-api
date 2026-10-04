# Build from the repository root: docker build -f services/saas-catalog-api/Dockerfile .
# Only the files declared in service.yaml data.reads are baked in; nothing else from the repo.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 SAAS_CATALOG_API_HOST=0.0.0.0 SAAS_CATALOG_API_ENV=production
WORKDIR /app
COPY packages/service-auth /app/packages/service-auth
COPY services/saas-catalog-api/pyproject.toml services/saas-catalog-api/server.py /app/services/saas-catalog-api/
RUN pip install /app/packages/service-auth /app/services/saas-catalog-api
COPY systems/cloud-platform/free-saas-master-catalog-2026.json /app/systems/cloud-platform/free-saas-master-catalog-2026.json

RUN useradd --system --uid 10001 app
USER app
EXPOSE 3490
HEALTHCHECK --interval=15s --timeout=3s --retries=3 CMD python -c "import os, urllib.request; port=os.environ.get('SAAS_CATALOG_API_PORT', os.environ.get('PORT', '3490')); urllib.request.urlopen('http://127.0.0.1:'+port+'/ready', timeout=2)"
CMD ["python", "/app/services/saas-catalog-api/server.py"]
