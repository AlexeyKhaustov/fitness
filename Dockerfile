FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# COPY templates /app/templates
COPY . .
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "fitness_app.wsgi"]