"""
Plot Geometry controller for plot marking, GPS management, and stitch operations.

Ports the Flask plot_marking.py endpoints to the framework backend.
All CSV/JSON data is stored in MinIO instead of the local filesystem.
"""
import io
import json
import csv

from litestar import Response
from litestar.handlers import get, post
from litestar.controller import Controller

from gemini.rest_api.models import RESTAPIError
from gemini.rest_api.controllers.files import minio_storage_provider, minio_storage_config
from gemini.api.plot_geometry_version import PlotGeometryVersion

from pydantic import BaseModel, Field
from typing import Optional, List, Any


# ── Request models ──────────────────────────────────────────────────────────

class DirectoryRequest(BaseModel):
    directory: str

class ImageRequest(BaseModel):
    directory: str
    image_name: str

class GpsReferenceRequest(BaseModel):
    directory: str
    lat: float
    lon: float

class GpsShiftRequest(BaseModel):
    directory: str
    current_lat: float
    current_lon: float

class VersionSaveRequest(BaseModel):
    directory: str
    state_snapshot: dict
    name: Optional[str] = None
    created_by: Optional[str] = None

class VersionLoadRequest(BaseModel):
    directory: str
    version: Optional[int] = Field(default=None, ge=1)

class VersionTargetRequest(BaseModel):
    directory: str
    version: int = Field(ge=1)

class VersionListRequest(BaseModel):
    directory: str

class MarkPlotRequest(BaseModel):
    directory: str
    start_image_name: str
    end_image_name: str
    plot_index: int
    camera: str = "top"
    stitch_direction: Optional[str] = None
    shift_all: Optional[bool] = False
    shift_amount: Optional[int] = 0
    original_start_image_index: Optional[int] = None

class DeletePlotRequest(BaseModel):
    directory: str
    plot_index: int

class SaveStitchMaskRequest(BaseModel):
    directory: str
    mask: Any

class FilterPlotBordersRequest(BaseModel):
    year: str
    experiment: str
    location: str
    population: str
    date: str

class StitchMaskCheckRequest(BaseModel):
    year: str
    experiment: str
    location: str
    population: str
    date: Optional[str] = None
    platform: Optional[str] = None
    sensor: Optional[str] = None

class PlotAssociationsRequest(BaseModel):
    year: str
    experiment: str
    location: str
    population: str
    date: str
    platform: str
    sensor: str

class AssociatePlotsRequest(BaseModel):
    year: str
    experiment: str
    location: str
    population: str
    date: str
    platform: str
    sensor: str
    agrowstitchDir: str
    boundaries: Any


# ── Helper functions ────────────────────────────────────────────────────────

def _bucket():
    return minio_storage_config.bucket_name


def _read_csv_from_minio(object_path: str) -> list:
    """Read a CSV file from MinIO and return list of dicts."""
    try:
        stream = minio_storage_provider.download_file_stream(
            object_name=object_path,
            bucket_name=_bucket(),
        )
        content = stream.read().decode("utf-8")
        stream.close()
        stream.release_conn()
        reader = csv.DictReader(io.StringIO(content))
        # Strip whitespace from column names
        rows = []
        for row in reader:
            rows.append({k.strip(): v for k, v in row.items()})
        return rows
    except Exception:
        return []


def _write_csv_to_minio(object_path: str, rows: list, fieldnames: list):
    """Write a list of dicts as CSV to MinIO."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    content = output.getvalue().encode("utf-8")
    minio_storage_provider.upload_file(
        bucket_name=_bucket(),
        object_name=object_path,
        data_stream=io.BytesIO(content),
        content_type="text/csv",
    )


def _read_json_from_minio(object_path: str) -> Optional[dict]:
    """Read a JSON file from MinIO."""
    try:
        stream = minio_storage_provider.download_file_stream(
            object_name=object_path,
            bucket_name=_bucket(),
        )
        content = stream.read().decode("utf-8")
        stream.close()
        stream.release_conn()
        return json.loads(content)
    except Exception:
        return None


def _write_json_to_minio(object_path: str, data: dict):
    """Write a JSON file to MinIO."""
    content = json.dumps(data, indent=2).encode("utf-8")
    minio_storage_provider.upload_file(
        bucket_name=_bucket(),
        object_name=object_path,
        data_stream=io.BytesIO(content),
        content_type="application/json",
    )


def _get_msgs_synced_path(directory: str) -> str:
    """Get the path to msgs_synced.csv for a given directory."""
    return f"{directory}/msgs_synced.csv"


def _get_population_path(directory: str) -> str:
    """Extract the population-level path from a sensor-level directory.
    e.g. Raw/2024/ExpA/Lincoln/Pop1/2024-06-01/Amiga/top -> Raw/2024/ExpA/Lincoln/Pop1
    """
    parts = directory.split("/")
    # Raw/{year}/{experiment}/{location}/{population}/...
    if len(parts) >= 5:
        return "/".join(parts[:5])
    return directory


def _find_image_row(rows: list, image_name: str):
    """Find a row by image name across all _file columns."""
    for i, row in enumerate(rows):
        for key, value in row.items():
            if key.strip().endswith("_file") or key.strip() == "rgb_file":
                if value and image_name in str(value):
                    return i, row
    return None, None


# ── Controller ──────────────────────────────────────────────────────────────

class PlotGeometryController(Controller):

    # -- Plot Data --

    @post(path="/data", sync_to_thread=True)
    def get_plot_data(self, data: DirectoryRequest) -> Any:
        """Get all marked plots in a dataset with metadata."""
        try:
            csv_path = _get_msgs_synced_path(data.directory)
            rows = _read_csv_from_minio(csv_path)
            if not rows:
                return []

            # Read plot_borders.csv if available
            pop_path = _get_population_path(data.directory)
            borders_path = f"{pop_path}/plot_borders.csv"
            borders = _read_csv_from_minio(borders_path)
            borders_map = {}
            for b in borders:
                idx = b.get("plot_index", "")
                if idx:
                    borders_map[str(idx)] = b

            plots = []
            seen_indices = set()
            for row in rows:
                plot_idx = str(row.get("plot_index", "-1")).strip()
                if plot_idx == "-1" or plot_idx == "" or plot_idx in seen_indices:
                    continue
                seen_indices.add(plot_idx)

                # Find first image for this plot
                image_name = ""
                for key, value in row.items():
                    if (key.strip().endswith("_file") or key.strip() == "rgb_file") and value:
                        image_name = str(value).strip()
                        break

                plot_info = {
                    "plot_index": int(plot_idx) if plot_idx.isdigit() else plot_idx,
                    "image_name": image_name,
                    "has_plot_metadata": plot_idx in borders_map,
                }
                if plot_idx in borders_map:
                    plot_info["Plot"] = borders_map[plot_idx].get("Plot", "")
                    plot_info["Accession"] = borders_map[plot_idx].get("Accession", "")

                plots.append(plot_info)

            return sorted(plots, key=lambda p: p.get("plot_index", 0))
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to get plot data"),
                status_code=500,
            )

    @post(path="/image_plot_index", sync_to_thread=True)
    def get_image_plot_index(self, data: ImageRequest) -> dict:
        """Get plot assignment for a specific image."""
        try:
            csv_path = _get_msgs_synced_path(data.directory)
            rows = _read_csv_from_minio(csv_path)

            _, row = _find_image_row(rows, data.image_name)
            if row is None:
                return {"plot_index": -1, "lat": None, "lon": None, "plot_name": None, "accession": None}

            plot_idx = int(row.get("plot_index", -1)) if str(row.get("plot_index", "")).strip().lstrip("-").isdigit() else -1
            lat = float(row.get("lat", 0)) if row.get("lat") else None
            lon = float(row.get("lon", 0)) if row.get("lon") else None

            # Get plot name/accession from borders
            plot_name = None
            accession = None
            if plot_idx >= 0:
                pop_path = _get_population_path(data.directory)
                borders = _read_csv_from_minio(f"{pop_path}/plot_borders.csv")
                for b in borders:
                    if str(b.get("plot_index", "")).strip() == str(plot_idx):
                        plot_name = b.get("Plot", "")
                        accession = b.get("Accession", "")
                        break

            return {
                "plot_index": plot_idx,
                "lat": lat,
                "lon": lon,
                "plot_name": plot_name,
                "accession": accession,
            }
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to get image plot index"),
                status_code=500,
            )

    @post(path="/max_index", sync_to_thread=True)
    def get_max_plot_index(self, data: DirectoryRequest) -> dict:
        """Get the highest plot_index currently marked."""
        try:
            csv_path = _get_msgs_synced_path(data.directory)
            rows = _read_csv_from_minio(csv_path)
            max_idx = -1
            for row in rows:
                idx_str = str(row.get("plot_index", "-1")).strip()
                if idx_str.lstrip("-").isdigit():
                    idx = int(idx_str)
                    if idx > max_idx:
                        max_idx = idx
            return {"max_plot_index": max_idx}
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to get max plot index"),
                status_code=500,
            )

    # -- GPS Data --

    @post(path="/gps_data", sync_to_thread=True)
    def get_gps_data(self, data: DirectoryRequest) -> Any:
        """Get all GPS coordinates from metadata."""
        try:
            csv_path = _get_msgs_synced_path(data.directory)
            rows = _read_csv_from_minio(csv_path)
            gps_data = []
            for row in rows:
                lat = row.get("lat", "")
                lon = row.get("lon", "")
                if lat and lon:
                    try:
                        gps_data.append({"lat": float(lat), "lon": float(lon)})
                    except ValueError:
                        continue
            return gps_data
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to get GPS data"),
                status_code=500,
            )

    # -- Stitch Direction --

    @post(path="/stitch_direction", sync_to_thread=True)
    def get_stitch_direction(self, data: DirectoryRequest) -> dict:
        """Get the saved stitch direction for a dataset."""
        try:
            txt_path = f"{data.directory}/stitch_direction.txt"
            try:
                stream = minio_storage_provider.download_file_stream(
                    object_name=txt_path, bucket_name=_bucket()
                )
                content = stream.read().decode("utf-8").strip()
                stream.close()
                stream.release_conn()
                return {"stitch_direction": content or None}
            except Exception:
                return {"stitch_direction": None}
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to get stitch direction"),
                status_code=500,
            )

    # -- GPS Reference --

    @post(path="/gps_reference", sync_to_thread=True)
    def get_gps_reference(self, data: DirectoryRequest) -> dict:
        """Retrieve the GPS reference point."""
        try:
            pop_path = _get_population_path(data.directory)
            ref = _read_json_from_minio(f"{pop_path}/gps_reference.json")
            if ref:
                return {"reference_lat": ref.get("lat"), "reference_lon": ref.get("lon")}
            return {"reference_lat": None, "reference_lon": None}
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to get GPS reference"),
                status_code=500,
            )

    @post(path="/set_gps_reference", sync_to_thread=True)
    def set_gps_reference(self, data: GpsReferenceRequest) -> dict:
        """Set a GPS reference point for coordinate shifting."""
        try:
            pop_path = _get_population_path(data.directory)
            _write_json_to_minio(f"{pop_path}/gps_reference.json", {"lat": data.lat, "lon": data.lon})
            return {"status": "success", "message": "GPS reference saved successfully"}
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to set GPS reference"),
                status_code=500,
            )

    # -- GPS Shifting --

    @post(path="/shift_gps", sync_to_thread=True)
    def shift_gps(self, data: GpsShiftRequest) -> dict:
        """Apply GPS coordinate shift to all metadata using reference point."""
        try:
            pop_path = _get_population_path(data.directory)
            ref = _read_json_from_minio(f"{pop_path}/gps_reference.json")
            if not ref:
                return Response(
                    content=RESTAPIError(error="No GPS reference set", error_description="Set a GPS reference first"),
                    status_code=400,
                )

            csv_path = _get_msgs_synced_path(data.directory)
            rows = _read_csv_from_minio(csv_path)
            if not rows:
                return Response(
                    content=RESTAPIError(error="No data", error_description="msgs_synced.csv not found or empty"),
                    status_code=404,
                )

            lat_shift = ref["lat"] - data.current_lat
            lon_shift = ref["lon"] - data.current_lon

            # Backup original coordinates
            backup = {"lat_shift": lat_shift, "lon_shift": lon_shift,
                       "reference_lat": ref["lat"], "reference_lon": ref["lon"],
                       "original_coords": [{"lat": r.get("lat", ""), "lon": r.get("lon", "")} for r in rows]}
            _write_json_to_minio(f"{pop_path}/gps_shift_backup.json", backup)

            # Apply shift
            for row in rows:
                if row.get("lat") and row.get("lon"):
                    try:
                        row["lat"] = str(float(row["lat"]) + lat_shift)
                        row["lon"] = str(float(row["lon"]) + lon_shift)
                    except ValueError:
                        continue

            fieldnames = list(rows[0].keys()) if rows else []
            _write_csv_to_minio(csv_path, rows, fieldnames)

            return {
                "status": "success",
                "message": f"GPS coordinates shifted by ({lat_shift:.6f}, {lon_shift:.6f})",
                "shift_applied": {"lat_shift": lat_shift, "lon_shift": lon_shift},
            }
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to shift GPS"),
                status_code=500,
            )

    @post(path="/undo_gps_shift", sync_to_thread=True)
    def undo_gps_shift(self, data: DirectoryRequest) -> dict:
        """Restore original GPS coordinates from backup."""
        try:
            pop_path = _get_population_path(data.directory)
            backup = _read_json_from_minio(f"{pop_path}/gps_shift_backup.json")
            if not backup:
                return Response(
                    content=RESTAPIError(error="No backup", error_description="No GPS shift backup found"),
                    status_code=404,
                )

            csv_path = _get_msgs_synced_path(data.directory)
            rows = _read_csv_from_minio(csv_path)
            original_coords = backup.get("original_coords", [])

            for i, row in enumerate(rows):
                if i < len(original_coords):
                    row["lat"] = original_coords[i].get("lat", row.get("lat", ""))
                    row["lon"] = original_coords[i].get("lon", row.get("lon", ""))

            fieldnames = list(rows[0].keys()) if rows else []
            _write_csv_to_minio(csv_path, rows, fieldnames)

            # Delete backup
            try:
                minio_storage_provider.delete_file(
                    object_name=f"{pop_path}/gps_shift_backup.json",
                    bucket_name=_bucket(),
                )
            except Exception:
                pass

            return {"status": "success", "message": "GPS coordinates restored to original values"}
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to undo GPS shift"),
                status_code=500,
            )

    @post(path="/gps_shift_status", sync_to_thread=True)
    def check_gps_shift_status(self, data: DirectoryRequest) -> dict:
        """Check if GPS shift has been applied."""
        try:
            pop_path = _get_population_path(data.directory)
            backup = _read_json_from_minio(f"{pop_path}/gps_shift_backup.json")
            if backup:
                return {
                    "has_shift": True,
                    "shift_applied": {
                        "lat_shift": backup.get("lat_shift"),
                        "lon_shift": backup.get("lon_shift"),
                        "reference_lat": backup.get("reference_lat"),
                        "reference_lon": backup.get("reference_lon"),
                    },
                }
            return {"has_shift": False, "shift_applied": None}
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to check GPS shift status"),
                status_code=500,
            )

    # -- Plot Marking --

    @post(path="/mark", sync_to_thread=True)
    def mark_plot(self, data: MarkPlotRequest) -> dict:
        """Mark a plot region between two images."""
        try:
            csv_path = _get_msgs_synced_path(data.directory)
            rows = _read_csv_from_minio(csv_path)
            if not rows:
                return Response(
                    content=RESTAPIError(error="No data", error_description="msgs_synced.csv not found"),
                    status_code=404,
                )

            start_idx, _ = _find_image_row(rows, data.start_image_name)
            end_idx, _ = _find_image_row(rows, data.end_image_name)

            if start_idx is None or end_idx is None:
                return Response(
                    content=RESTAPIError(error="Image not found", error_description="Could not find start or end image"),
                    status_code=404,
                )

            # Ensure start <= end
            if start_idx > end_idx:
                start_idx, end_idx = end_idx, start_idx

            # Mark all rows in range
            for i in range(start_idx, end_idx + 1):
                rows[i]["plot_index"] = str(data.plot_index)

            fieldnames = list(rows[0].keys())
            _write_csv_to_minio(csv_path, rows, fieldnames)

            return {"status": "success", "message": f"Plot {data.plot_index} marked successfully."}
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to mark plot"),
                status_code=500,
            )

    @post(path="/delete", sync_to_thread=True)
    def delete_plot(self, data: DeletePlotRequest) -> dict:
        """Delete a marked plot by setting its plot_index to -1."""
        try:
            csv_path = _get_msgs_synced_path(data.directory)
            rows = _read_csv_from_minio(csv_path)
            if not rows:
                return Response(
                    content=RESTAPIError(error="No data", error_description="msgs_synced.csv not found"),
                    status_code=404,
                )

            for row in rows:
                if str(row.get("plot_index", "")).strip() == str(data.plot_index):
                    row["plot_index"] = "-1"

            fieldnames = list(rows[0].keys())
            _write_csv_to_minio(csv_path, rows, fieldnames)

            return {"status": "success", "message": f"Plot {data.plot_index} deleted successfully."}
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to delete plot"),
                status_code=500,
            )

    # -- Stitch Mask --

    @post(path="/stitch_mask/save", sync_to_thread=True)
    def save_stitch_mask(self, data: SaveStitchMaskRequest) -> dict:
        """Save binary mask for stitching operations."""
        try:
            pop_path = _get_population_path(data.directory)
            _write_json_to_minio(f"{pop_path}/stitch_mask.json", {"mask": data.mask})
            return {"status": "success", "message": "Mask saved successfully."}
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to save stitch mask"),
                status_code=500,
            )

    @post(path="/stitch_mask/check", sync_to_thread=True)
    def check_stitch_mask(self, data: StitchMaskCheckRequest) -> dict:
        """Check if a stitch mask exists for a dataset."""
        try:
            base = f"Raw/{data.year}/{data.experiment}/{data.location}/{data.population}"
            if data.date and data.platform and data.sensor:
                base = f"{base}/{data.date}/{data.platform}/{data.sensor}"
            mask_data = _read_json_from_minio(f"{base}/stitch_mask.json")
            if mask_data:
                return {"exists": True, "mask": mask_data.get("mask")}
            # Also check at population level
            pop_base = f"Raw/{data.year}/{data.experiment}/{data.location}/{data.population}"
            mask_data = _read_json_from_minio(f"{pop_base}/stitch_mask.json")
            if mask_data:
                return {"exists": True, "mask": mask_data.get("mask")}
            return {"exists": False, "mask": None}
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to check stitch mask"),
                status_code=500,
            )

    # -- Plot Borders --

    @post(path="/borders", sync_to_thread=True)
    def get_plot_borders(self, data: FilterPlotBordersRequest) -> dict:
        """Get plot border GeoJSON data."""
        try:
            borders_path = f"Processed/{data.year}/{data.experiment}/{data.location}/{data.population}/Plot-Boundary-WGS84.geojson"
            geojson = _read_json_from_minio(borders_path)
            if geojson:
                return {"plot_data": geojson, "geojson": geojson}

            # Fallback: try plot_borders.csv
            csv_borders_path = f"Raw/{data.year}/{data.experiment}/{data.location}/{data.population}/{data.date}/plot_borders.csv"
            rows = _read_csv_from_minio(csv_borders_path)
            if rows:
                plot_data = {}
                for row in rows:
                    idx = row.get("plot_index", "")
                    if idx:
                        plot_data[idx] = {
                            "plot": row.get("Plot", ""),
                            "accession": row.get("Accession", ""),
                            "start_lat": row.get("start_lat", ""),
                            "start_lon": row.get("start_lon", ""),
                            "end_lat": row.get("end_lat", ""),
                            "end_lon": row.get("end_lon", ""),
                        }
                return {"plot_data": plot_data}

            return {"plot_data": {}}
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to get plot borders"),
                status_code=500,
            )

    # -- AgRowStitch Plot Associations --

    @post(path="/associations", sync_to_thread=True)
    def get_agrowstitch_associations(self, data: PlotAssociationsRequest) -> dict:
        """Get AgRowStitch plot associations."""
        try:
            assoc_path = (
                f"Processed/{data.year}/{data.experiment}/{data.location}/"
                f"{data.population}/{data.date}/{data.platform}/{data.sensor}/"
                f"plot_associations.json"
            )
            assoc_data = _read_json_from_minio(assoc_path)
            if assoc_data:
                return {
                    "associations": assoc_data.get("associations", {}),
                    "total_plots": assoc_data.get("total_plots", 0),
                }
            return {"associations": {}, "total_plots": 0}
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to get plot associations"),
                status_code=500,
            )

    @post(path="/associate", sync_to_thread=True)
    def associate_plots_with_boundaries(self, data: AssociatePlotsRequest) -> dict:
        """Associate AgRowStitch plots with field boundaries."""
        try:
            # Read AgRowStitch plot images
            agrowstitch_path = (
                f"Processed/{data.year}/{data.experiment}/{data.location}/"
                f"{data.population}/{data.date}/{data.platform}/{data.sensor}/"
                f"{data.agrowstitchDir}"
            )

            # List files in the agrowstitch directory
            items = minio_storage_provider.list_files(
                bucket_name=_bucket(),
                prefix=agrowstitch_path,
            )
            plot_files = [
                item.object_name for item in items
                if item.object_name.endswith(".png") or item.object_name.endswith(".jpg")
            ]

            boundaries = data.boundaries
            if isinstance(boundaries, dict) and "features" in boundaries:
                features = boundaries["features"]
            else:
                features = []

            # Simple association: match plot files to boundary features by index
            associations = {}
            for i, plot_file in enumerate(sorted(plot_files)):
                filename = plot_file.split("/")[-1]
                if i < len(features):
                    props = features[i].get("properties", {})
                    associations[filename] = {
                        "plot_index": props.get("plot_index", i),
                        "plot_name": props.get("Plot", props.get("plot_label", "")),
                    }

            # Save associations
            assoc_path = (
                f"Processed/{data.year}/{data.experiment}/{data.location}/"
                f"{data.population}/{data.date}/{data.platform}/{data.sensor}/"
                f"plot_associations.json"
            )
            _write_json_to_minio(assoc_path, {
                "associations": associations,
                "total_plots": len(features),
            })

            return {
                "status": "success",
                "associations": len(associations),
                "message": f"Associated {len(associations)} plots with boundaries",
            }
        except Exception as e:
            return Response(
                content=RESTAPIError(error=str(e), error_description="Failed to associate plots"),
                status_code=500,
            )

    # ------------------------------------------------------------------
    # Versioning — named snapshots of plot-geometry state per directory.
    # ------------------------------------------------------------------

    @post(path="/versions/save", sync_to_thread=True)
    def save_version(self, data: VersionSaveRequest) -> dict:
        version = PlotGeometryVersion.save(
            directory=data.directory,
            state_snapshot=data.state_snapshot,
            name=data.name,
            created_by=data.created_by,
        )
        if version is None:
            return Response(
                content=RESTAPIError(
                    error="Version not saved",
                    error_description="Failed to save plot-geometry version.",
                ),
                status_code=500,
            )
        return {
            "version": version.version,
            "name": version.name,
            "is_active": version.is_active,
            "created_at": version.created_at.isoformat() if version.created_at else None,
        }

    @post(path="/versions/list", sync_to_thread=True)
    def list_versions(self, data: VersionListRequest) -> List[dict]:
        versions = PlotGeometryVersion.list_for_directory(directory=data.directory)
        return [
            {
                "version": v.version,
                "name": v.name,
                "is_active": v.is_active,
                "created_at": v.created_at.isoformat() if v.created_at else None,
                "created_by": v.created_by,
            }
            for v in versions
        ]

    @post(path="/versions/load", sync_to_thread=True)
    def load_version(self, data: VersionLoadRequest) -> dict:
        version = PlotGeometryVersion.load(
            directory=data.directory, version=data.version
        )
        if version is None:
            return Response(
                content=RESTAPIError(
                    error="Version not found",
                    error_description=(
                        "No matching version found for the given directory."
                    ),
                ),
                status_code=404,
            )
        return {
            "version": version.version,
            "name": version.name,
            "is_active": version.is_active,
            "created_at": version.created_at.isoformat() if version.created_at else None,
            "created_by": version.created_by,
            "state_snapshot": version.state_snapshot,
        }

    @post(path="/versions/activate", sync_to_thread=True)
    def activate_version(self, data: VersionTargetRequest) -> dict:
        version = PlotGeometryVersion.activate(
            directory=data.directory, version=data.version
        )
        if version is None:
            return Response(
                content=RESTAPIError(
                    error="Version not found",
                    error_description="No matching version to activate.",
                ),
                status_code=404,
            )
        return {
            "version": version.version,
            "name": version.name,
            "is_active": version.is_active,
        }

    @post(path="/versions/delete", sync_to_thread=True)
    def delete_version(self, data: VersionTargetRequest) -> dict:
        ok = PlotGeometryVersion.delete_version(
            directory=data.directory, version=data.version
        )
        if not ok:
            return Response(
                content=RESTAPIError(
                    error="Version not found",
                    error_description="No matching version to delete.",
                ),
                status_code=404,
            )
        return {"status": "deleted", "version": data.version}
