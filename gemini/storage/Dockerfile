# quay.io, not Docker Hub: the docker.io/minio/minio repository was
# removed upstream, so `FROM minio/minio:latest` now fails the build with
# "pull access denied / repository does not exist". quay.io/minio is
# MinIO's own registry and still carries the image. Machines with a
# cached copy kept building, which is why this only surfaced in CI.
FROM quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z
