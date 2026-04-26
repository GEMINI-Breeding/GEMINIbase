FROM python:3.12-slim

WORKDIR /app

COPY gemini/workers/odm/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY gemini/__init__.py /app/gemini/__init__.py
# Copy the whole workers/ tree so shared modules (auth.py, base.py, types.py)
# stay in sync with what BaseWorker imports. The earlier per-file COPY list
# missed `auth.py` when Phase 6 added worker JWT auth, restart-looping the
# odm worker.
COPY gemini/workers/ /app/gemini/workers/

CMD ["python", "-m", "gemini.workers.odm.worker"]
