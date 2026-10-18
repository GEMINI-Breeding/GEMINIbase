FROM python:3.12-slim

# System deps: GDAL for rasterio/geopandas, OpenGL libs for opencv-headless.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY gemini/workers/ml/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Model backends (Hugging Face, local Ultralytics weights). CPU-only torch
# first, from PyTorch's CPU index — the default wheel bundles CUDA (~2 GB more)
# that this container can't use without GPU passthrough. The GPU variant
# (geminibase-worker-ml-gpu, amd64 only) is the same image built with
# TORCH_INDEX set to a CUDA index; it uses an NVIDIA card when the container is
# given one (`--gpus`), and the CPU otherwise. Ultralytics pulls in
# the GUI build of OpenCV, which needs libGL and clashes with the headless one;
# swap it back.
COPY gemini/workers/ml/requirements-models.txt /app/requirements-models.txt
ARG TORCH_INDEX=https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir --index-url ${TORCH_INDEX} \
        torch torchvision \
    && pip install --no-cache-dir -r /app/requirements-models.txt -c /app/requirements.txt \
    && pip uninstall -y opencv-python opencv-python-headless \
    && pip install --no-cache-dir -c /app/requirements.txt opencv-python-headless

# Downloaded models live on the model-cache volume mounted at /models, so
# they survive container rebuilds: HF Hub models under huggingface/,
# uploaded weights under weights/ (see worker._download_weights).
# YOLO_AUTOINSTALL=false: Ultralytics otherwise pip-installs packages it
# thinks are missing at run time — seen upgrading numpy 1.26 → 2.x mid-job.
RUN mkdir -p /opt/ultralytics
ENV GEMINI_MODEL_CACHE_DIR=/models \
    HF_HOME=/models/huggingface \
    YOLO_CONFIG_DIR=/opt/ultralytics \
    YOLO_AUTOINSTALL=false

COPY gemini/workers/ /app/gemini/workers/
COPY gemini/__init__.py /app/gemini/__init__.py

CMD ["python", "-m", "gemini.workers.ml.worker"]
