FROM python:3.12-slim

WORKDIR /app

COPY gemini/workers/odm/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY gemini/__init__.py /app/gemini/__init__.py
COPY gemini/workers/__init__.py /app/gemini/workers/__init__.py
COPY gemini/workers/base.py /app/gemini/workers/base.py
COPY gemini/workers/types.py /app/gemini/workers/types.py
COPY gemini/workers/odm/ /app/gemini/workers/odm/

CMD ["python", "-m", "gemini.workers.odm.worker"]
