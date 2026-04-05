FROM python:3.12-slim

# Install system dependencies for OpenCV headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY gemini/workers/flir/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy worker code (includes bin_to_images.py extraction module)
COPY gemini/workers/ /app/gemini/workers/
COPY gemini/__init__.py /app/gemini/__init__.py

CMD ["python", "-m", "gemini.workers.flir.worker"]
