"""Unit tests for the dataset-path migration helpers.

End-to-end migration is exercised live (Phase 6 validation step) — these
tests pin the pure key-rewrite logic so the live run can't silently
mutate keys in surprising ways.
"""
import sys

from gemini.api._dataset_path_migration import (
    new_key_for as _new_key_for,
    short_id_from_uuid as _short_id_from_uuid,
)


class TestShortIdFromUuid:
    def test_hyphenated_uuid(self):
        assert (
            _short_id_from_uuid("a2f31b04-1234-4abc-8def-0123456789ab")
            == "a2f31b04"
        )

    def test_unhyphenated_hex(self):
        assert (
            _short_id_from_uuid("a2f31b0412344abc8def0123456789ab")
            == "a2f31b04"
        )

    def test_uppercase_normalized_to_lowercase(self):
        assert (
            _short_id_from_uuid("A2F31B04-1234-4ABC-8DEF-0123456789AB")
            == "a2f31b04"
        )

    def test_none_returns_none(self):
        assert _short_id_from_uuid(None) is None


class TestNewKeyFor:
    def test_legacy_image_path_gets_short_id_segment(self):
        out = _new_key_for(
            "Raw/2026/GEMINI/Davis/Cowpea MAGIC/2026-05-15/Drone/Thermal/Images/foo.jpg",
            "a2f31b04",
        )
        assert out == (
            "Raw/2026/GEMINI/Davis/Cowpea MAGIC/2026-05-15/Drone/Thermal/"
            "a2f31b04/Images/foo.jpg"
        )

    def test_already_migrated_returns_none(self):
        # Idempotent: a key that already has a hex segment before
        # /Images/ is left alone.
        assert (
            _new_key_for(
                "Raw/2026/GEMINI/Davis/Cowpea MAGIC/2026-05-15/Drone/Thermal/"
                "a2f31b04/Images/foo.jpg",
                "a2f31b04",
            )
            is None
        )

    def test_processed_path_returns_none(self):
        # `Processed/...` outputs are scope-wide; the migration should
        # not touch them.
        assert (
            _new_key_for(
                "Processed/2026/GEMINI/Davis/Cowpea/2026-05-15/Drone/RGB/"
                "odm_orthophoto.tif",
                "a2f31b04",
            )
            is None
        )

    def test_wizard_supplemental_path_returns_none(self):
        # `Raw/{date}/{exp}/...` doesn't have an Images/ segment.
        assert (
            _new_key_for(
                "Raw/2026-05-06/GEMINI/SupplementalData.xlsx",
                "a2f31b04",
            )
            is None
        )

    def test_sidecar_under_images_gets_migrated_too(self):
        # A weird file that landed under Images/ but isn't an image —
        # still gets migrated because the layout (not the contents) is
        # what we're rewriting.
        out = _new_key_for(
            "Raw/2026/GEMINI/Davis/Cowpea/2026-05-15/Drone/RGB/Images/notes.txt",
            "8f1c47de",
        )
        assert out == (
            "Raw/2026/GEMINI/Davis/Cowpea/2026-05-15/Drone/RGB/"
            "8f1c47de/Images/notes.txt"
        )

    def test_path_with_spaces_in_population(self):
        out = _new_key_for(
            "Raw/2026/GEMINI/Davis/Cowpea MAGIC/2026-05-15/Drone/RGB/Images/x.png",
            "a2f31b04",
        )
        assert out == (
            "Raw/2026/GEMINI/Davis/Cowpea MAGIC/2026-05-15/Drone/RGB/"
            "a2f31b04/Images/x.png"
        )


class TestRunMigrationOrdering:
    """Copy -> update DB row -> remove old object."""

    LEGACY = "Raw/2026/GEMINI/Davis/Cowpea/2026-05-15/Drone/RGB/Images/x.jpg"
    DS_ID = "a2f31b04-1234-4abc-8def-0123456789ab"

    def _run(self, test_client, monkeypatch, fail_update=False):
        from unittest.mock import MagicMock, patch

        monkeypatch.setenv("GEMINI_ADMIN_MIGRATIONS_ENABLED", "1")
        # minio is stubbed as a plain module by the root conftest.
        monkeypatch.setitem(
            sys.modules, "minio.commonconfig", MagicMock()
        )
        mod = "gemini.rest_api.controllers.migrate_dataset_paths"
        calls = []
        client = MagicMock()
        client.copy_object.side_effect = lambda *a, **k: calls.append("copy")
        client.remove_object.side_effect = lambda *a, **k: calls.append("remove")

        list_session = MagicMock()
        list_session.execute.return_value.all.return_value = [
            ("fid", "gemini", self.LEGACY, self.DS_ID)
        ]
        upd_session = MagicMock()

        def _upd(*a, **k):
            calls.append("update")
            if fail_update:
                raise RuntimeError("db down")

        upd_session.execute.side_effect = _upd
        ds_session = MagicMock()
        ds_session.execute.return_value.all.return_value = []
        sessions = iter([list_session, upd_session, ds_session])
        engine = MagicMock()
        engine.get_session.side_effect = lambda: MagicMock(
            __enter__=MagicMock(return_value=next(sessions)),
            __exit__=MagicMock(return_value=False),
        )
        provider = MagicMock(client=client)
        with patch(f"{mod}.db_engine", engine), \
                patch(f"{mod}.minio_storage_provider", provider):
            res = test_client.post("/api/migrate_dataset_paths")
        assert res.status_code == 200, res.text
        return calls, res.json()

    def test_db_updated_before_old_object_removed(self, test_client, monkeypatch):
        calls, body = self._run(test_client, monkeypatch)
        assert calls == ["copy", "update", "remove"]
        assert body["migrated"] == 1

    def test_db_failure_keeps_old_object(self, test_client, monkeypatch):
        calls, body = self._run(test_client, monkeypatch, fail_update=True)
        assert calls == ["copy", "update"]
        assert body["migrated"] == 0
        assert body["errors"][0]["error"] == "db down"
