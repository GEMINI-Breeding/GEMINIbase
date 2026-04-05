FROM python:3.12-slim

# Install GDAL system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY gemini/workers/geo/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy worker code
COPY gemini/workers/ /app/gemini/workers/
COPY gemini/__init__.py /app/gemini/__init__.py

CMD ["python", "-m", "gemini.workers.geo.worker"]
