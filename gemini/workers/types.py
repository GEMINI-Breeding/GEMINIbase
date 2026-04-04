"""
Job type definitions and parameter schemas for processing workers.
"""
from enum import Enum


class JobType(str, Enum):
    """Valid processing job types."""
    TRAIN_MODEL = "TRAIN_MODEL"
    LOCATE_PLANTS = "LOCATE_PLANTS"
    EXTRACT_TRAITS = "EXTRACT_TRAITS"
    RUN_STITCH = "RUN_STITCH"
    RUN_ODM = "RUN_ODM"
    SPLIT_ORTHOMOSAIC = "SPLIT_ORTHOMOSAIC"
    PROCESS_DRONE_TIFF = "PROCESS_DRONE_TIFF"
    TIF_TO_PNG = "TIF_TO_PNG"
    CREATE_COG = "CREATE_COG"
    EXTRACT_BINARY = "EXTRACT_BINARY"


class JobStatus(str, Enum):
    """Job status values."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# Maps job types to the worker service that handles them
JOB_TYPE_WORKER_MAP = {
    JobType.TRAIN_MODEL: "gemini-worker-ml",
    JobType.LOCATE_PLANTS: "gemini-worker-ml",
    JobType.EXTRACT_TRAITS: "gemini-worker-ml",
    JobType.RUN_STITCH: "gemini-worker-stitch",
    JobType.RUN_ODM: "gemini-worker-odm",
    JobType.SPLIT_ORTHOMOSAIC: "gemini-worker-odm",
    JobType.PROCESS_DRONE_TIFF: "gemini-worker-geo",
    JobType.TIF_TO_PNG: "gemini-worker-geo",
    JobType.CREATE_COG: "gemini-worker-geo",
    JobType.EXTRACT_BINARY: "gemini-worker-flir",
}
