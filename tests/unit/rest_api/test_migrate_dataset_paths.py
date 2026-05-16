"""Unit tests for the dataset-path migration helpers.

End-to-end migration is exercised live (Phase 6 validation step) — these
tests pin the pure key-rewrite logic so the live run can't silently
mutate keys in surprising ways.
"""
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
