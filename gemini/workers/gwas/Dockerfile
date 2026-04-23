# Pin to linux/amd64: the prebuilt GEMMA + PLINK2 binaries we download below
# are x86_64-only. On Apple Silicon this runs under emulation — slower to
# build but correct. Production deployment is linux/amd64 anyway.
FROM --platform=linux/amd64 python:3.12-slim

# Build-time system deps for GEMMA + PLINK binaries.
# (Package name on Debian 13 / trixie is libgsl28; older distros used libgsl27.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates unzip libgomp1 libopenblas0 libgsl28 zlib1g \
 && rm -rf /var/lib/apt/lists/*

# Install PLINK 2.0 (static linux x86_64)
RUN curl -fsSL https://s3.amazonaws.com/plink2-assets/alpha6/plink2_linux_x86_64_20250129.zip \
      -o /tmp/plink2.zip \
 && unzip /tmp/plink2.zip -d /usr/local/bin/ \
 && chmod +x /usr/local/bin/plink2 \
 && rm /tmp/plink2.zip

# Install GEMMA (static linux binary)
RUN curl -fsSL https://github.com/genetics-statistics/GEMMA/releases/download/v0.98.5/gemma-0.98.5-linux-static-AMD64.gz \
      -o /tmp/gemma.gz \
 && gunzip /tmp/gemma.gz && mv /tmp/gemma /usr/local/bin/gemma \
 && chmod +x /usr/local/bin/gemma

WORKDIR /gemini-framework

COPY gemini/workers/gwas/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY gemini /gemini-framework/gemini

ENV PYTHONPATH=/gemini-framework
CMD ["python", "-m", "gemini.workers.gwas.worker"]
