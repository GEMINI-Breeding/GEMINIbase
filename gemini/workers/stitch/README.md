# `gemini/workers/stitch/` — RUN_STITCH worker

Drives [AgRowStitch](https://github.com/GEMINI-Breeding/AgRowStitch) in
process for ground-level image stitching. Replaces the pre-migration
FastAPI backend's PyInstaller-subprocess channel with a direct
in-process call to `AgRowStitch.run(config_path, cpu_count)`.

## One-time setup

AgRowStitch is not on PyPI and lives in its own repo, so it is vendored
as a nested git submodule:

```bash
cd backend   # the GEMINIbase submodule of GEMINI-App
git submodule add \
    https://github.com/GEMINI-Breeding/AgRowStitch.git \
    gemini/workers/stitch/vendor/AgRowStitch
git commit -m "Vendor AgRowStitch into the stitch worker"
```

Then uncomment the `geminibase-worker-stitch` service in
`gemini/pipeline/docker-compose.yaml` and rebuild:

```bash
docker compose -f gemini/pipeline/docker-compose.yaml up -d --build geminibase-worker-stitch
```

The Dockerfile puts `gemini/workers/stitch/vendor/AgRowStitch` on
`PYTHONPATH` so `import AgRowStitch` resolves at runtime.

## Runtime knobs

The worker reads a `parameters` dict with:

- `image_paths: List[str]` — MinIO object paths, in stitch order
- `output_mosaic_path: str` — MinIO object path to write the mosaic
- `config: dict` — AgRowStitch knobs (device, direction, mask, batch_size, …)
- `cpu_count: int` — parallelism (defaults to CPU count minus 1)

Submit via `POST /api/jobs/submit` with `job_type=RUN_STITCH`.
