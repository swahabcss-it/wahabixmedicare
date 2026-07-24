FROM python:3.11-slim

# Set workdir to /app
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set WORKDIR to where manage.py and config folder actually reside inside container
WORKDIR /app/wms

EXPOSE 8000

# Run migrations, seed, static collect and start gunicorn
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py seed_demo_data && python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3"]