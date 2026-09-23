# Native on amd64 and arm64. PLINK 2 and GEMMA come from Debian (trixie, the
# base image's release), which packages exactly the versions this worker was
# validated with; upstream publishes no Linux arm64 binaries of either. The
# version check fails the build if the base image ever moves to other
# versions — re-validate GWAS results before updating the expected strings.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    plink2 gemma ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && plink2 --version | grep -F "v2.0.0-a.6.9 " \
 && gemma 2>&1 | grep -F "GEMMA 0.98.5 "

WORKDIR /geminibase

COPY gemini/workers/gwas/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY gemini /geminibase/gemini

ENV PYTHONPATH=/geminibase
CMD ["python", "-m", "gemini.workers.gwas.worker"]
