# LandLynk worker. Shapely and pyproj ship manylinux wheels with their native
# libraries bundled, so a slim Python base builds reliably without system GDAL.
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first for layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY migrations ./migrations
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
# Railway provides $PORT; default to 8000 for local runs.
CMD ["sh", "-c", "uvicorn landlynk_worker.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
