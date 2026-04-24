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
    RUN_GWAS = "RUN_GWAS"


class JobStatus(str, Enum):
    """Job status values."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# Documentation-only map of job types to the compose service that claims them.
# Not used by dispatch — workers self-claim types via their `supported_job_types`
# set. Kept in sync with docker-compose.yaml service names as a lookup aid.
JOB_TYPE_WORKER_MAP = {
    JobType.TRAIN_MODEL: "geminibase-worker-ml",
    JobType.LOCATE_PLANTS: "geminibase-worker-ml",
    JobType.EXTRACT_TRAITS: "geminibase-worker-ml",
    JobType.RUN_STITCH: "geminibase-worker-stitch",
    JobType.RUN_ODM: "geminibase-worker-odm",
    JobType.SPLIT_ORTHOMOSAIC: "geminibase-worker-geo",
    JobType.PROCESS_DRONE_TIFF: "geminibase-worker-geo",
    JobType.TIF_TO_PNG: "geminibase-worker-geo",
    JobType.CREATE_COG: "geminibase-worker-geo",
    JobType.EXTRACT_BINARY: "geminibase-worker-flir",
    JobType.RUN_GWAS: "geminibase-worker-gwas",
}
