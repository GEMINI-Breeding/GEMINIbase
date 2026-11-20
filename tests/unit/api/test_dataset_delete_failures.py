"""Dataset.delete must not report success, or remove files, when the DB side fails.

The dataset row is deleted through the real BaseModel.delete with a session
that fails, the way a lock timeout or FK violation would.
"""
from contextlib import ExitStack, contextmanager
from datetime import date
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from gemini.api.dataset import Dataset

MODULE = "gemini.api.dataset"
RECORD_MODELS = [
    "gemini.db.models.columnar.trait_records.TraitRecordModel",
    "gemini.db.models.columnar.sensor_records.SensorRecordModel",
    "gemini.db.models.columnar.dataset_records.DatasetRecordModel",
    "gemini.db.models.columnar.procedure_records.ProcedureRecordModel",
    "gemini.db.models.columnar.script_records.ScriptRecordModel",
    "gemini.db.models.columnar.model_records.ModelRecordModel",
]


@pytest.fixture
def env():
    """Patch everything Dataset.delete touches; yield the mocks by name."""
    session = MagicMock()
    engine = MagicMock()

    @contextmanager
    def get_session():
        yield session

    engine.get_session = get_session
    mocks = {"session": session}
    with ExitStack() as stack:
        stack.enter_context(patch("gemini.db.core.base.db_engine", engine))
        stack.enter_context(
            patch(f"{MODULE}.DatasetModel.get", return_value=MagicMock())
        )
        stack.enter_context(
            patch(f"{MODULE}._collect_dataset_file_targets",
                  return_value=[("row-1", "gemini", "experiment_files/a.jpg")])
        )
        mocks["delete_file_rows"] = stack.enter_context(
            patch(f"{MODULE}._delete_experiment_file_rows")
        )
        mocks["minio"] = stack.enter_context(
            patch("gemini.api.base.minio_storage_provider")
        )
        mocks["sweep"] = stack.enter_context(
            patch("gemini.api.base.sweep_minio_prefixes")
        )
        mocks["record_deletes"] = [
            stack.enter_context(patch(f"{path}.delete_by_dataset"))
            for path in RECORD_MODELS
        ]
        stack.enter_context(
            patch.object(Dataset, "get_associated_experiments",
                         return_value=[MagicMock(experiment_name="Exp")])
        )
        yield mocks


def _dataset():
    return Dataset(id=uuid4(), dataset_name="DS", collection_date=date(2024, 6, 15), dataset_type_id=1)


def _assert_files_untouched(env):
    env["minio"].client.remove_object.assert_not_called()
    env["delete_file_rows"].assert_not_called()
    env["sweep"].assert_not_called()


def test_row_delete_failure_reports_failure_and_keeps_files(env):
    env["session"].delete.side_effect = Exception("lock timeout")
    assert _dataset().delete() is False
    _assert_files_untouched(env)


def test_record_sweep_failure_keeps_dataset_row_and_files(env):
    env["record_deletes"][0].side_effect = Exception("lock timeout")
    assert _dataset().delete() is False
    # The remaining sweeps still ran, so a retry has less left to do...
    for helper in env["record_deletes"][1:]:
        helper.assert_called_once_with("DS")
    # ...but the dataset row stays so the retry can find it.
    env["session"].delete.assert_not_called()
    _assert_files_untouched(env)


def test_success_removes_row_and_files(env):
    assert _dataset().delete() is True
    env["session"].delete.assert_called_once()
    env["minio"].client.remove_object.assert_called_once_with(
        bucket_name="gemini", object_name="experiment_files/a.jpg"
    )
    env["delete_file_rows"].assert_called_once_with(["row-1"])
    env["sweep"].assert_called_once_with(["dataset_data/Exp/DS/"])
