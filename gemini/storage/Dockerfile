# MinIO RELEASE.2025-09-07T16-13-09Z, from our own published copy.
#
# MinIO no longer distributes images publicly: docker.io/minio/minio was
# removed, and quay.io/minio (checked 2026-09-24) now answers every tag with
# 401 Unauthorized. Our storage image at sha-0fb532b is exactly that MinIO
# release (this Dockerfile was a bare FROM), for amd64 and arm64, and is
# public, so it is the base now — pinned by digest so it can't change.
# Moving to a newer MinIO means building it from source (MinIO's community
# edition is source-only now) or another S3 server: see merge_plan.md.
FROM ghcr.io/gemini-breeding/geminibase-storage@sha256:0550d8f045ad5e2e78bc4570d7cb157ab1508c52e0c7a3edb2e53208f3e2854e
