# One-shot MinIO setup (service account, policy, buckets), run on every
# stack start by the `storage-init` service. The script is baked in so the
# production stack needs no source checkout; the dev stack builds this too.
# Build context: gemini/storage.
#
# Base: the mc client (RELEASE.2025-08-13T08-35-41Z) from our own published
# storage-init image at sha-0fb532b, pinned by digest — quay.io/minio/mc now
# requires authentication (see ../Dockerfile). The script is copied over the
# old one, so edits to it still take effect.
FROM ghcr.io/gemini-breeding/geminibase-storage-init@sha256:5d16dee76c17ae9306499bb1a0c4ac413b6ff5901fecc57c83840b1d67c28ab0
COPY scripts/init_minio.sh /usr/local/bin/init_minio.sh
ENTRYPOINT ["/bin/sh", "/usr/local/bin/init_minio.sh"]
