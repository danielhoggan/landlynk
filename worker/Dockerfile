# LandLynk worker. Shapely and pyproj ship manylinux wheels with their native
# libraries bundled, so a slim Python base builds reliably without system GDAL.
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first for layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Document font for the PDF export. Poppins is open (SIL OFL); fetched at build
# so generated PDFs embed it. If the fetch fails the renderer falls back to
# Helvetica at runtime, so the build is never blocked on font availability.
ENV LANDLYNK_FONT_DIR=/app/fonts
RUN mkdir -p /app/fonts && python -c "\
import urllib.request as u; \
base='https://github.com/google/fonts/raw/main/ofl/poppins/'; \
[u.urlretrieve(base+f, '/app/fonts/'+f) for f in ('Poppins-Regular.ttf','Poppins-SemiBold.ttf')]" \
    || echo 'Poppins fetch failed; PDF falls back to Helvetica'

COPY src ./src
COPY migrations ./migrations
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
# Railway provides $PORT; default to 8000 for local runs.
CMD ["sh", "-c", "uvicorn landlynk_worker.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
