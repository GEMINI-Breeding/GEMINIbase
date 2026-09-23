# One-shot MinIO setup (service account, policy, buckets), run on every
# stack start by the `storage-init` service. The script is baked in so the
# production stack needs no source checkout; the dev stack builds this too.
# Build context: gemini/storage.
FROM quay.io/minio/mc:RELEASE.2025-08-13T08-35-41Z
COPY scripts/init_minio.sh /usr/local/bin/init_minio.sh
ENTRYPOINT ["/bin/sh", "/usr/local/bin/init_minio.sh"]
