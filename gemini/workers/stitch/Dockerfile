FROM python:3.12-slim

# System deps for opencv, torch, git-based pip installs, and the lightglue fetch.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libglib2.0-0 \
    libgomp1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps (torch + opencv + lightglue are heavy).
COPY gemini/workers/stitch/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the worker code + the vendored AgRowStitch. The vendor directory is
# expected to be a git submodule at gemini/workers/stitch/vendor/AgRowStitch/.
# Adding it to PYTHONPATH lets `import AgRowStitch` resolve at runtime.
COPY gemini/workers/ /app/gemini/workers/
COPY gemini/__init__.py /app/gemini/__init__.py
ENV PYTHONPATH="/app/gemini/workers/stitch/vendor/AgRowStitch:${PYTHONPATH}"

CMD ["python", "-m", "gemini.workers.stitch.worker"]
