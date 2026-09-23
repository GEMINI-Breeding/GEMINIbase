# `gemini/workers/stitch/` — RUN_STITCH worker

Per-plot ground-image stitching with
[AgRowStitch](https://github.com/GEMINI-Breeding/AgRowStitch), then
georeferencing of each plot along the rover's GPS track and a combined
mosaic. A port of GEMINI-App main's `ground.run_stitching` /
`run_georeferencing` (`geo_utils.py`).

## Pinned dependencies

AgRowStitch is not on PyPI. The Dockerfile clones the exact commit
GEMINI-App main vendors (`backend/vendor/AgRowStitch` @ `25cf015`, branch
`opencv`) and applies `agrowstitch-opencv413.patch` — main's fix for the
OpenCV ≥ 4.13 segfault (`match.H = None`). LightGlue is pinned to main's
vendored commit (`eb42fee`) in `requirements.txt`; its SuperPoint and
LightGlue weights are downloaded at build time, not per job.

To move to a newer AgRowStitch, change `AGROWSTITCH_REF` in the
Dockerfile, check the patch still applies (the build fails if not), and
rebuild:

```bash
docker compose up -d --build geminibase-worker-stitch
```

Torch is the CPU build. `device: gpu` falls back to CPU unless the image
is rebuilt with CUDA torch and the container is given a GPU.

## Job parameters

| key | |
|---|---|
| `images_prefix` | MinIO prefix of the track's top-camera frames (`…/RGB/Images/top/`) |
| `msgs_synced_path` | the track's `msgs_synced.csv` (frame names, lat/lon, direction) |
| `plots` | `[{plot_id, start_image, end_image, direction}]` from Plot Marking; `direction` is `up`/`down`/`left`/`right` |
| `output_prefix` | where this stitch version goes (`…/AgRowStitch_v{N}/`) |
| `settings` | `forward_limit`, `max_reprojection_error`, `batch_size`, `min_inliers`, `crop_rules` |
| `custom_options` | raw AgRowStitch options, applied last (unknown keys are dropped and listed in the manifest) |
| `device`, `num_cpu` | `cpu` / `gpu` / `multiprocessing`; `num_cpu` 0 = all but one |

Crop rules are chosen per plot as in main: the first rule whose headings
include the plot's dominant GPS heading (or, for a direction rule, whose
directions include the plot's marked direction); a rule listing none
matches every plot.

## Outputs (under `output_prefix`)

- `full_res_mosaic_temp_plot_{id}.png` — each stitched plot
- `georeferenced_plot_{id}_utm.tif` — each plot as a UTM GeoTIFF
- `combined_mosaic_utm.tif`, `combined_mosaic.tif` (WGS84, nodata 0)
- `plot_borders.csv` — the markings used, with start/end GPS
- `stitch_manifest.json` — settings, per-plot result and footprint

A failed plot is recorded in the manifest and skipped; the job fails if
no plot stitches. Each plot's AgRowStitch run is a child process, so a
cancel kills it and a native crash fails only that plot.
