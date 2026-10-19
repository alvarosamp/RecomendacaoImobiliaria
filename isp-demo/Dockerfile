FROM python:3.12-alpine
WORKDIR /app
COPY server.py planner.py ./
COPY web ./web
COPY data/simulation.json data/roads.json data/radar.json ./data/
RUN addgroup -S demo && adduser -S demo -G demo
USER demo
ENV HOST=0.0.0.0 PORT=8080 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2)"
CMD ["python", "server.py"]
