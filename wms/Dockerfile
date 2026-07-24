FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set Django settings module explicitly
ENV DJANGO_SETTINGS_MODULE=config.settings

# Add dummy DATABASE_URL and SECRET_KEY during build time
RUN SECRET_KEY=build-time-placeholder-not-used-at-runtime \
    DEBUG=False \
    DATABASE_URL=sqlite:////tmp/db.sqlite3 \
    python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]