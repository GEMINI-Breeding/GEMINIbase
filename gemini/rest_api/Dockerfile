FROM python:3.12

RUN echo "Debug: Building image"

# Genomic toolchain (Phase 9d'): plink2 packs/unpacks PGEN, bcftools
# converts VCF↔BCF and computes per-variant stats, tabix indexes BCF
# for region queries. The rest-api owns the genomic ingest path that
# transcodes uploads into PGEN+BCF in MinIO; the GWAS worker container
# already has these tools but we now need them here too.
#
# bcftools + tabix come from Debian. plink2 we install from the
# upstream prebuilt binary — same as the GWAS worker container does
# (gemini/workers/gwas/Dockerfile) so both code paths behave
# identically. Without the version pin Debian's plink2 may diverge
# from what the worker expects.
RUN apt-get update && apt-get install -y --no-install-recommends \
        bcftools \
        tabix \
        unzip \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://s3.amazonaws.com/plink2-assets/alpha6/plink2_linux_x86_64_20250129.zip \
      -o /tmp/plink2.zip \
 && unzip /tmp/plink2.zip -d /usr/local/bin/ \
 && chmod +x /usr/local/bin/plink2 \
 && rm /tmp/plink2.zip

# Install poetry
RUN pip install poetry

# Set the working directory
WORKDIR /geminibase

# Install poetry dependencies
COPY pyproject.toml poetry.lock README.md ./

RUN poetry config virtualenvs.create false

RUN poetry install --no-root

# Install Pillow for image thumbnail generation
RUN pip install "Pillow>=10.0.0,<12.0.0"

# Copy the complete GEMINI source code into the container
COPY gemini ./gemini

# Copy Alembic config so rest-api can run migrations on startup when
# GEMINI_RUN_MIGRATIONS=1. Day-0 schema still comes from init_sql/
# executed by the Postgres container; Alembic owns schema evolution.
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic

# Entrypoint: optionally run migrations, then exec the real command
# (compose.yaml'ss `command:` arg wins over the default CMD below).
COPY gemini/rest_api/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Add GEMINIbase to the PYTHONPATH
ENV PYTHONPATH="${PYTHONPATH}:/geminibase"

# Expose GEMINI API port
EXPOSE 7777

# Expose Debugpy
EXPOSE 5678

# Production default — overridden in compose.yaml for dev (adds --reload).
CMD ["poetry", "run", "litestar", "--app", "gemini.rest_api.app:app", "run", "--host", "0.0.0.0", "--port", "7777"]

