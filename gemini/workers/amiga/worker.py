"""
farm-ng Amiga OAK binary extraction worker.

Handles EXTRACT_BINARY jobs: downloads Amiga .bin event files from MinIO,
runs the farm_ng-based extraction pipeline (RGB images, disparity maps,
GPS metadata), and uploads results back to MinIO.
"""
import logging
import os
import re
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Set

from gemini.workers.base import BaseWorker
from gemini.workers.types import JobType

logger = logging.getLogger(__name__)

STORAGE_HOST = os.environ.get("GEMINI_STORAGE_HOSTNAME", "gemini-storage")
STORAGE_PORT = os.environ.get("GEMINI_STORAGE_PORT", "9000")
STORAGE_ACCESS_KEY = os.environ.get("GEMINI_STORAGE_ACCESS_KEY", "")
STORAGE_SECRET_KEY = os.environ.get("GEMINI_STORAGE_SECRET_KEY", "")
STORAGE_BUCKET = os.environ.get("GEMINI_STORAGE_BUCKET_NAME", "gemini")

# MinIO PUTs for the output tree are I/O-bound and the dominant cost of
# the job — a typical .bin decodes to hundreds of small JPEGs + NPYs.
# Bumped to 16 from 8 after profiling showed the pool was thread-blocked
# on the per-file `register` HTTP fan-out (now batched at end-of-upload),
# leaving MinIO PUTs underutilising the connection pool.
UPLOAD_POOL_SIZE = 16
CLEANUP_POOL_SIZE = 4
# Tunes for the progress-reporting side. report_progress() PATCHes
# /api/jobs/.../status, which is cheap server-side but still a network
# round trip per call — we throttle the upload-phase emits so we
# don't fan out 1200+ tiny PATCHes during a 30s upload.
UPLOAD_PROGRESS_MIN_INTERVAL_S = 0.5
EXTRACT_PROGRESS_POLL_INTERVAL_S = 0.5


def _get_minio_client():
    """Construct a MinIO client whose HTTP connection pool is big
    enough for our parallel upload + download workloads.

    minio-py's default ``urllib3.PoolManager`` ships with
    ``maxsize=10`` per host. With UPLOAD_POOL_SIZE=16 upload
    threads each calling ``fput_object`` concurrently, 6 threads
    constantly lose their connection to ``Connection pool is full,
    discarding connection`` and pay TCP-handshake overhead on
    every PUT. That was the actual cause of the "hang at 95%"
    behaviour: the upload phase took ~2 minutes longer than it
    should because most of the pool was thrashing.

    A small headroom over UPLOAD_POOL_SIZE absorbs incidental
    `stat_object` / `remove_object` calls that race the upload
    pool (e.g. the download-phase stat fan-out at job start).
    """
    import urllib3
    from minio import Minio

    pool_size = max(UPLOAD_POOL_SIZE + 4, 20)
    http_client = urllib3.PoolManager(
        num_pools=10,
        maxsize=pool_size,
        block=False,
        retries=urllib3.Retry(
            total=3,
            backoff_factor=0.2,
            status_forcelist=[500, 502, 503, 504],
        ),
    )
    return Minio(
        f"{STORAGE_HOST}:{STORAGE_PORT}",
        access_key=STORAGE_ACCESS_KEY,
        secret_key=STORAGE_SECRET_KEY,
        secure=False,
        http_client=http_client,
    )


def _extract_timestamp(filename: str) -> str:
    """Extract timestamp from Amiga binary filename for sorting."""
    match = re.match(r"(\d{4}_\d{2}_\d{2}_\d{2}_\d{2}_\d{2}_\d+)", filename)
    return match.group(1) if match else filename


class AmigaWorker(BaseWorker):
    """Worker for farm-ng Amiga OAK binary extraction."""

    @property
    def supported_job_types(self) -> Set[JobType]:
        return {JobType.EXTRACT_BINARY}

    def process(self, job_id: str, job_type: str, parameters: dict) -> dict:
        if job_type == JobType.EXTRACT_BINARY.value:
            return self._extract_binary_job(job_id, parameters)
        raise ValueError(f"Unsupported job type: {job_type}")

    def _make_throttled_cancel_check(self, job_id: str, min_interval_s: float = 2.0):
        """Return a closure that calls is_cancelled() at most once per
        `min_interval_s` seconds.

        is_cancelled() does an HTTP GET against the rest-api, which
        goes through WorkerSession's _send_lock. The upload pool's
        as_completed loop fires once per uploaded file (thousands per
        job); the download stream loop fires once per 1 MiB chunk.
        At 16 threads × thousands of files those calls serialize on
        the session lock and dominate the visible runtime. Cached
        result between intervals — fast path is a single
        time.monotonic() compare.

        First call always hits the API so cancellation that happened
        before the job started is detected immediately.
        """
        state = {"last_check": 0.0, "last_value": False}
        send_lock = threading.Lock()  # cache writes are not thread-safe

        def check() -> bool:
            now = time.monotonic()
            with send_lock:
                if (
                    state["last_check"] == 0.0
                    or now - state["last_check"] >= min_interval_s
                ):
                    state["last_check"] = now
                    state["last_value"] = self.is_cancelled(job_id)
                return state["last_value"]

        return check

    def _register_extracted_files_batch(
        self,
        experiment_id: str,
        dataset_id: str | None,
        bucket: str,
        object_names: list[str],
    ) -> None:
        """POST a single batch of (bucket, object_name) entries to
        /api/files/register_batch. One HTTP round trip + one DB
        transaction for the whole upload phase, instead of N. Failures
        are warning-logged; the files are still in MinIO and fall
        back to the experiment-cascade prefix backstop."""
        if not object_names:
            return
        try:
            self._http.post(
                "/api/files/register_batch",
                json={
                    "experiment_id": experiment_id,
                    "dataset_id": dataset_id,
                    "files": [
                        {"bucket": bucket, "object_name": n}
                        for n in object_names
                    ],
                },
            )
        except Exception as exc:
            logger.warning(
                "register_batch (%d files) for experiment %s failed: %s",
                len(object_names), experiment_id, exc,
            )

    def _spawn_extract_progress_poller(
        self,
        job_id: str,
        progress_path: Path,
        total_files: int,
        stop_event: threading.Event,
        progress_range: tuple[float, float] = (30.0, 70.0),
    ) -> threading.Thread:
        """Start a background thread that polls ``RGB/progress.txt``
        (written by bin_to_images.py during decode) and emits
        ``report_progress`` updates so the UI bar moves during the
        otherwise-silent extraction phase.

        ``progress.txt`` contains a single float of the form
        ``<file_index>.<fractional-completion-of-current-file>``; the
        per-file portion is < 1.0 so the value is in ``[0, total_files]``.
        We map that to the [start, end] percent range allocated to the
        extraction stage.
        """
        start_pct, end_pct = progress_range
        span = end_pct - start_pct

        def _poll():
            last_emitted = -1.0
            while not stop_event.is_set():
                try:
                    raw = progress_path.read_text().strip()
                    val = float(raw) if raw else 0.0
                    frac = min(1.0, max(0.0, val / max(total_files, 1)))
                    pct = start_pct + span * frac
                    # Emit only when the bar would actually advance by
                    # at least 0.5% — keeps the PATCH chatter sane.
                    if pct - last_emitted >= 0.5:
                        self.report_progress(job_id, pct, {
                            "stage": "extracting",
                            "files_done": int(val),
                            "total_files": total_files,
                        })
                        last_emitted = pct
                except FileNotFoundError:
                    # bin_to_images hasn't written the file yet — keep
                    # waiting silently. Happens for the first ~second.
                    pass
                except Exception as exc:
                    logger.debug("extract progress poll failed: %s", exc)
                stop_event.wait(EXTRACT_PROGRESS_POLL_INTERVAL_S)

        t = threading.Thread(target=_poll, name="amiga-extract-progress", daemon=True)
        t.start()
        return t

    def _unregister_extracted_file(self, bucket: str, object_name: str) -> None:
        """POST to /api/files/unregister so the now-removed .bin's
        pointer row goes away. Best-effort."""
        try:
            self._http.post(
                "/api/files/unregister",
                json={"bucket": bucket, "object_name": object_name},
            )
        except Exception as exc:
            logger.warning(
                "unregister %s/%s failed: %s", bucket, object_name, exc,
            )

    def _extract_binary_job(self, job_id: str, parameters: dict) -> dict:
        """
        Extract Amiga .bin files into RGB images, disparity maps, and GPS metadata.

        Parameters (from job submission):
            files: list of filenames (e.g. ["2024_01_15_12_30_45_001.bin", ...])
            localDirPath: MinIO object prefix where files were uploaded
                          (e.g. "2024/Exp1/Field1/Pop1/2024-01-15/Amiga/OAK/Amiga")
        """
        file_list = parameters.get("files", [])
        dir_path = parameters.get("localDirPath", "")
        # Post-migration-0007 the frontend creates a dataset before
        # submitting EXTRACT_BINARY and forwards its id here so this
        # worker's outputs can be registered as `experiment_files`
        # rows pointing at that dataset. The dataset_id is optional
        # for backwards compatibility — old extract jobs without one
        # still write their files to MinIO; they just won't be
        # reachable by per-dataset delete (only the experiment
        # cascade catches them via the Processed/ prefix backstop).
        dataset_id = parameters.get("dataset_id") or parameters.get("datasetId")
        experiment_id = parameters.get("experiment_id") or parameters.get("experimentId")

        # Filter to .bin files only and sort by timestamp
        bin_files = sorted(
            [f for f in file_list if f.endswith(".bin")],
            key=_extract_timestamp,
        )

        if not bin_files:
            return {"status": "skipped", "message": "No .bin files to extract"}

        # Throttled cancel-check used inside the hot loops (download
        # stream, upload pool, cleanup). Calling self.is_cancelled
        # directly there means thousands of HTTP GETs per job
        # serialized through WorkerSession._send_lock — that was
        # responsible for the ~2-minute "stuck at 95%" gap.
        cancelled = self._make_throttled_cancel_check(job_id)

        client = _get_minio_client()

        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            # Step 1: Download .bin files from MinIO. We stream
            # rather than calling fget_object so the progress bar can
            # advance during the download of a single large .bin —
            # the previous "fget then report" path made the bar sit
            # at 5% for the full 30+ seconds of download.
            self.report_progress(job_id, 5, {"stage": "downloading", "total_files": len(bin_files)})
            local_bin_paths = []
            n_files = len(bin_files)
            # Total bytes across all files (pre-stat'd so we can
            # weight progress by bytes, not just file count).
            file_sizes: list[int] = []
            for filename in bin_files:
                try:
                    stat = client.stat_object(STORAGE_BUCKET, f"{dir_path}/{filename}")
                    file_sizes.append(stat.size or 0)
                except Exception:
                    file_sizes.append(0)
            total_bytes = max(sum(file_sizes), 1)
            bytes_done = 0
            last_dl_emit = 0.0
            for i, filename in enumerate(bin_files):
                if cancelled():
                    return {"status": "cancelled"}

                object_name = f"{dir_path}/{filename}"
                local_path = str(input_dir / filename)
                logger.info(f"Downloading {object_name} from MinIO")
                resp = None
                try:
                    resp = client.get_object(STORAGE_BUCKET, object_name)
                    with open(local_path, "wb") as fh:
                        for chunk in resp.stream(amt=1024 * 1024):  # 1 MiB
                            if cancelled():
                                return {"status": "cancelled"}
                            fh.write(chunk)
                            bytes_done += len(chunk)
                            now = time.monotonic()
                            # Throttle to ~2 emits/sec or every 0.5%
                            # bar movement, whichever is sooner.
                            if now - last_dl_emit >= 0.5:
                                last_dl_emit = now
                                dl_progress = 5 + (25 * bytes_done / total_bytes)
                                self.report_progress(job_id, dl_progress, {
                                    "stage": "downloading",
                                    "file": filename,
                                    "bytes_downloaded": bytes_done,
                                    "total_bytes": total_bytes,
                                    "downloaded": i,
                                    "total_files": n_files,
                                })
                finally:
                    if resp is not None:
                        try:
                            resp.close()
                            resp.release_conn()
                        except Exception:
                            pass
                local_bin_paths.append(local_path)
                # Always emit at the boundary so the bar lands at the
                # right value when a file completes (even if the last
                # in-loop emit was throttled).
                dl_progress = 5 + (25 * bytes_done / total_bytes)
                self.report_progress(job_id, dl_progress, {
                    "stage": "downloading",
                    "file": filename,
                    "downloaded": i + 1,
                    "total_files": n_files,
                })

            if self.is_cancelled(job_id):
                return {"status": "cancelled"}

            # Step 2: Run extraction. bin_to_images writes
            # ``output/RGB/progress.txt`` continuously during decode;
            # spin a poller thread to translate that into job progress
            # so the UI bar moves through this phase instead of
            # sitting frozen at 30% for ~70s on a typical .bin.
            self.report_progress(job_id, 30, {"stage": "extracting"})
            extract_stop = threading.Event()
            extract_progress_path = output_dir / "RGB" / "progress.txt"
            extract_thread = self._spawn_extract_progress_poller(
                job_id=job_id,
                progress_path=extract_progress_path,
                total_files=len(local_bin_paths),
                stop_event=extract_stop,
            )
            try:
                from gemini.workers.amiga.bin_to_images import extract_binary
                extract_binary(local_bin_paths, output_dir)
            except Exception as e:
                raise RuntimeError(f"Binary extraction failed: {e}") from e
            finally:
                extract_stop.set()
                extract_thread.join(timeout=2.0)
            # Make sure the bar lands at the end of the extract band
            # before the upload phase resets it.
            self.report_progress(job_id, 70, {"stage": "extracting"})

            if self.is_cancelled(job_id):
                return {"status": "cancelled"}

            # Step 3: Upload results back to MinIO (parallel — this is the
            # dominant cost of the job, hundreds of small files per .bin).
            self.report_progress(job_id, 70, {"stage": "uploading"})

            # The output directory has structure:
            #   RGB/
            #     Metadata/ (CSVs)
            #     Images/{camera}/ (JPEGs)
            #   Disparity/{camera}/ (NPY)
            #   progress.txt, report.txt
            files_to_upload = []
            for root, _dirs, filenames in os.walk(str(output_dir)):
                for fname in filenames:
                    if fname == "progress.txt":
                        continue  # Skip progress file — not needed in storage
                    local_file = os.path.join(root, fname)
                    relative = os.path.relpath(local_file, str(output_dir))
                    parent_dir = str(Path(dir_path).parent)
                    object_name = f"{parent_dir}/{relative}"
                    files_to_upload.append((local_file, object_name))

            total = len(files_to_upload)
            counter_lock = threading.Lock()
            counter = {"n": 0}
            last_emit = {"t": 0.0, "n": -1}

            def _upload_one(item):
                local_file, object_name = item
                # Pure MinIO write — the per-file `register` HTTP
                # call has been hoisted out of the inner loop into a
                # single batch POST after the pool drains. That
                # change is what makes the thread pool actually
                # parallel: previously each thread serialized on
                # the shared `WorkerSession.request()` retry/lock,
                # collapsing the 8-way pool to effectively single-
                # threaded.
                client.fput_object(STORAGE_BUCKET, object_name, local_file)
                with counter_lock:
                    counter["n"] += 1
                    done = counter["n"]
                    now = time.monotonic()
                    # Throttle progress emits to one per
                    # UPLOAD_PROGRESS_MIN_INTERVAL_S OR per 1% step,
                    # whichever is sooner. Always emit on the final
                    # file so the bar lands cleanly at 95%.
                    should_emit = (
                        done == total
                        or (now - last_emit["t"]) >= UPLOAD_PROGRESS_MIN_INTERVAL_S
                    )
                    if should_emit:
                        last_emit["t"] = now
                        last_emit["n"] = done
                if should_emit:
                    upload_progress = 70 + (25 * done / max(total, 1))
                    self.report_progress(job_id, upload_progress, {
                        "stage": "uploading",
                        "uploaded": done,
                        "total_files": total,
                    })

            with ThreadPoolExecutor(max_workers=UPLOAD_POOL_SIZE) as pool:
                futures = [pool.submit(_upload_one, item) for item in files_to_upload]
                try:
                    for fut in as_completed(futures):
                        # Throttled — see _make_throttled_cancel_check.
                        # The naive `self.is_cancelled` fires once per
                        # uploaded file (thousands per job) and was
                        # serializing through WorkerSession's send
                        # lock, eating ~2 minutes of "hang at 95%".
                        if cancelled():
                            for pending in futures:
                                pending.cancel()
                            return {"status": "cancelled"}
                        fut.result()  # re-raise any per-task exception
                except Exception:
                    for pending in futures:
                        pending.cancel()
                    raise

            uploaded_count = counter["n"]

            # Register every uploaded object as an experiment_files
            # row in one batch POST. Single DB transaction; the
            # per-dataset delete cascade will sweep these rows when
            # the user trashes the dataset.
            if experiment_id and files_to_upload:
                self.report_progress(job_id, 95, {
                    "stage": "registering",
                    "uploaded": uploaded_count,
                    "total_files": total,
                })
                self._register_extracted_files_batch(
                    experiment_id=experiment_id,
                    dataset_id=dataset_id,
                    bucket=STORAGE_BUCKET,
                    object_names=[obj_name for _, obj_name in files_to_upload],
                )

            # Step 4: Clean up — delete original .bin files from MinIO.
            self.report_progress(job_id, 95, {"stage": "cleanup"})

            def _remove_one(filename):
                object_name = f"{dir_path}/{filename}"
                try:
                    client.remove_object(STORAGE_BUCKET, object_name)
                except Exception as e:
                    logger.warning(f"Failed to delete {object_name}: {e}")
                # Drop the original .bin's experiment_files row so it
                # doesn't dangle as a pointer to a removed object. The
                # frontend wrote this row via the chunked-upload
                # finalize when the .bin first landed; without
                # unregister here the cascade would still try to
                # remove a now-nonexistent object and log a warning.
                self._unregister_extracted_file(
                    bucket=STORAGE_BUCKET,
                    object_name=object_name,
                )

            with ThreadPoolExecutor(max_workers=CLEANUP_POOL_SIZE) as pool:
                for _ in pool.map(_remove_one, bin_files):
                    pass

        return {
            "status": "completed",
            "extracted_files": uploaded_count,
            "bin_files_processed": len(bin_files),
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    worker = AmigaWorker()
    worker.run()
