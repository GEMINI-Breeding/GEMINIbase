FROM python:3.12-slim

# exiftool is the only general-purpose extractor that understands the
# FLIR APP1 block embedded in radiometric JPEGs (Planck constants +
# RawThermalImage PNG). libgomp1 is pulled in by numpy/Pillow runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libexpat1 \
    libgomp1 \
    libimage-exiftool-perl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY gemini/workers/thermal/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the whole workers/ tree so this worker can import the shared
# BaseWorker / auth / types modules, plus gemini/__init__.py to make
# the package importable.
COPY gemini/workers/ /app/gemini/workers/
COPY gemini/__init__.py /app/gemini/__init__.py

CMD ["python", "-m", "gemini.workers.thermal.worker"]
