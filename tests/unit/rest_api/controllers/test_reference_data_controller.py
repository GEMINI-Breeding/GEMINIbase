"""Tests for the reference-data controller: keeping a pointer to the original file."""
from unittest.mock import MagicMock, patch

MODULE = "gemini.rest_api.controllers.reference_data"
MINIO_PATH = f"{MODULE}.minio_storage_provider"

CSV = b"plot_id,LAI\n1,2.5\n2,3.0\n"


class TestOriginalObjectInfo:

    @patch(MINIO_PATH)
    def test_records_an_existing_object(self, mock_minio):
        from gemini.rest_api.controllers.reference_data import _original_object_info

        mock_minio.file_exists.return_value = True
        assert _original_object_info("ReferenceData/E/S/P/lai.csv") == {
            "original_object": "ReferenceData/E/S/P/lai.csv"
        }

    @patch(MINIO_PATH)
    def test_skips_a_missing_object(self, mock_minio):
        from gemini.rest_api.controllers.reference_data import _original_object_info

        mock_minio.file_exists.return_value = False
        assert _original_object_info("ReferenceData/nope.csv") is None

    @patch(MINIO_PATH)
    def test_no_pointer_no_lookup(self, mock_minio):
        from gemini.rest_api.controllers.reference_data import _original_object_info

        assert _original_object_info(None) is None
        assert _original_object_info("") is None
        mock_minio.file_exists.assert_not_called()

    @patch(MINIO_PATH)
    def test_storage_error_is_not_fatal(self, mock_minio):
        from gemini.rest_api.controllers.reference_data import _original_object_info

        mock_minio.file_exists.side_effect = Exception("minio down")
        assert _original_object_info("ReferenceData/x.csv") is None


class TestUploadStoresPointer:

    def _upload(self, test_client, **params):
        return test_client.post(
            "/api/reference_data/upload",
            params={
                "name": "Hand LAI",
                "column_mapping_json": '{"plot_id": "plot_id", "LAI": "LAI"}',
                **params,
            },
            files={"file": ("lai.csv", CSV, "text/csv")},
        )

    @patch(MINIO_PATH)
    @patch(f"{MODULE}.ReferenceDataset")
    def test_upload_passes_dataset_info(self, mock_ds, mock_minio, test_client):
        mock_minio.file_exists.return_value = True
        created = MagicMock()
        created.insert_plots.return_value = 2
        created.id = "11111111-1111-1111-1111-111111111111"
        created.name = "Hand LAI"
        created.experiment = created.location = created.population = None
        created.dataset_date = None
        created.trait_columns = ["LAI"]
        created.dataset_info = {"original_object": "ReferenceData/lai.csv"}
        created.created_at = None
        mock_ds.create.return_value = created

        response = self._upload(test_client, original_object="ReferenceData/lai.csv")

        assert response.status_code == 201, response.text
        kwargs = mock_ds.create.call_args.kwargs
        assert kwargs["dataset_info"] == {"original_object": "ReferenceData/lai.csv"}
        assert response.json()["plot_count"] == 2

    @patch(MINIO_PATH)
    @patch(f"{MODULE}.ReferenceDataset")
    def test_upload_without_pointer(self, mock_ds, mock_minio, test_client):
        created = MagicMock()
        created.insert_plots.return_value = 2
        created.id = "11111111-1111-1111-1111-111111111111"
        created.name = "Hand LAI"
        created.experiment = created.location = created.population = None
        created.dataset_date = None
        created.trait_columns = ["LAI"]
        created.dataset_info = None
        created.created_at = None
        mock_ds.create.return_value = created

        response = self._upload(test_client)

        assert response.status_code == 201, response.text
        assert mock_ds.create.call_args.kwargs["dataset_info"] is None
        mock_minio.file_exists.assert_not_called()
