FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY migrations ./migrations

EXPOSE 9999
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9999", "--workers", "2"]
