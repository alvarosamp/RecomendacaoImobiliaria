FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl libgomp1 fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements-api.txt ./
COPY deploy/hostinger/constraints.txt ./hostinger-constraints.txt
RUN pip install --no-cache-dir -r requirements-api.txt -c hostinger-constraints.txt pillow pytest httpx
RUN apt-get update && apt-get install -y --no-install-recommends libexpat1 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir huggingface-hub==2.1.1
COPY src/ src/
COPY api/ api/
COPY config/ config/
# The Dockerfile-specific allowlist includes only audited public references.
# Optional sources (such as the IBGE GeoPackage) need not exist to run demos.
COPY data/official/ reference-data/official/
COPY deploy/hostinger/start.py /app/start.py
ENV PYTHONPATH=/app/src PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd --create-home --uid 10001 appuser && mkdir -p data storage models cache output && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["python", "/app/start.py"]
