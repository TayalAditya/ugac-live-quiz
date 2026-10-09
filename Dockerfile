FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system quiz && adduser --system --ingroup quiz quiz

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=quiz:quiz . .
USER quiz

EXPOSE 5001

CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--worker-class", "gthread", "--workers", "1", "--threads", "100", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
