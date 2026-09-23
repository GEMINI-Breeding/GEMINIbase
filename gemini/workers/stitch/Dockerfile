FROM python:3.12-slim

# System deps for opencv, torch and the git-based installs.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libglib2.0-0 \
    libgomp1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# CPU-only torch: the CUDA wheels are several GB and this worker runs on CPU.
RUN pip install --no-cache-dir torch torchvision \
    --index-url https://download.pytorch.org/whl/cpu

COPY gemini/workers/stitch/requirements.txt /app/requirements.txt
# LightGlue depends on the GUI opencv-python, whose cv2 then shadows the
# headless build and needs libGL. Keep only the headless one.
RUN pip install --no-cache-dir -r /app/requirements.txt \
    && pip uninstall -y opencv-python \
    && pip install --no-cache-dir --force-reinstall --no-deps \
       "opencv-python-headless>=4.13,<5"

# AgRowStitch isn't on PyPI. Install the exact commit GEMINI-App main
# vendors (backend/vendor/AgRowStitch @ 25cf015, branch "opencv"), with
# main's OpenCV 4.13 fix applied, so stitching behaves as it does there.
ARG AGROWSTITCH_REF=25cf015459ac533f4daaa10327eee1918b00abe1
COPY gemini/workers/stitch/agrowstitch-opencv413.patch /tmp/agrowstitch.patch
RUN git clone https://github.com/GEMINI-Breeding/AgRowStitch.git /opt/AgRowStitch \
    && cd /opt/AgRowStitch \
    && git checkout --quiet "$AGROWSTITCH_REF" \
    && git apply /tmp/agrowstitch.patch \
    && rm -rf .git Test_Images /tmp/agrowstitch.patch
ENV PYTHONPATH="/opt/AgRowStitch"

# Bake in the SuperPoint + LightGlue weights AgRowStitch loads, so a job
# never depends on reaching github.com at run time.
RUN python -c "from lightglue import LightGlue, SuperPoint; \
SuperPoint(max_num_keypoints=2048); LightGlue(features='superpoint')"

COPY gemini/workers/ /app/gemini/workers/
COPY gemini/__init__.py /app/gemini/__init__.py

CMD ["python", "-m", "gemini.workers.stitch.worker"]
