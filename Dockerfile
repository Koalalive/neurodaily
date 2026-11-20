FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/app

WORKDIR /app
COPY pyproject.toml ./
COPY neurodaily ./neurodaily
RUN pip install --no-cache-dir .

EXPOSE 8031
CMD ["sh", "-c", "python -m neurodaily config init || true; python -m neurodaily serve --host 0.0.0.0 --port 8031"]
