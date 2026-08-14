FROM mcr.microsoft.com/playwright/python:v1.61.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
WORKDIR /app/src

# Render inyecta $PORT en tiempo de ejecucion; 10000 es solo un valor por
# defecto razonable si se ejecuta el contenedor fuera de Render.
ENV PORT=10000
EXPOSE 10000

# Un unico worker: cada request lanza su propio Chromium (memoria pesada),
# no queremos varios a la vez en un plan gratuito/pequeño. Timeout alto
# porque el login + scraping completo puede tardar bastante mas en un
# servidor compartido que en local.
CMD ["sh", "-c", "gunicorn -w 1 -b 0.0.0.0:${PORT} --timeout 180 app:app"]
