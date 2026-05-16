"""Unit tests for the ODM worker's MinIO prefix helpers.

These pin the path shape RUN_ODM consumes against accidental drift,
including the new `dataset_short_id` segment that isolates per-upload
prefixes (post Option-A migration).
"""


class TestBuildScopePrefix:
    """`_build_scope_prefix` returns `Raw/.../{sensor}/` (no Images,
    no shortId). It's the read root for scope-wide artifacts:
    image_filter.txt, gcp_list.txt, geo.txt, gcp_locations.csv,
    gcp_image_groups.json. These survive multi-dataset selection
    because they describe the scope, not any one upload."""

    def test_full_scope(self):
        from gemini.workers.odm.worker import _build_scope_prefix

        out = _build_scope_prefix({
            "year": "2024",
            "experiment": "GEMINI",
            "location": "Davis",
            "population": "Cowpea MAGIC",
            "date": "2024-07-25",
            "platform": "Drone",
            "sensor": "RGB",
        })
        assert out == "Raw/2024/GEMINI/Davis/Cowpea MAGIC/2024-07-25/Drone/RGB/"

    def test_skips_empty_segments(self):
        from gemini.workers.odm.worker import _build_scope_prefix

        out = _build_scope_prefix({
            "year": "2024",
            "experiment": "GEMINI",
            "date": "2024-07-25",
            "platform": "Drone",
            "sensor": "RGB",
        })
        assert out == "Raw/2024/GEMINI/2024-07-25/Drone/RGB/"


class TestBuildImagePrefix:
    """`_build_image_prefix` returns the leaf image directory.
    Post-migration that's `Raw/.../{sensor}/{shortId}/Images/`; for
    legacy callers without a shortId it collapses to
    `Raw/.../{sensor}/Images/`."""

    def test_with_dataset_short_id(self):
        from gemini.workers.odm.worker import _build_image_prefix

        out = _build_image_prefix({
            "year": "2024",
            "experiment": "GEMINI",
            "location": "Davis",
            "population": "Cowpea MAGIC",
            "date": "2024-07-25",
            "platform": "Drone",
            "sensor": "RGB",
            "dataset_short_id": "a2f31b04",
        })
        assert out == (
            "Raw/2024/GEMINI/Davis/Cowpea MAGIC/2024-07-25/Drone/RGB/"
            "a2f31b04/Images/"
        )

    def test_without_dataset_short_id_falls_back_to_legacy(self):
        from gemini.workers.odm.worker import _build_image_prefix

        out = _build_image_prefix({
            "year": "2024",
            "experiment": "GEMINI",
            "location": "Davis",
            "population": "Cowpea MAGIC",
            "date": "2024-07-25",
            "platform": "Drone",
            "sensor": "RGB",
        })
        assert out == (
            "Raw/2024/GEMINI/Davis/Cowpea MAGIC/2024-07-25/Drone/RGB/Images/"
        )


class TestBuildOutputPrefix:
    """`_build_output_prefix` deliberately excludes `dataset_short_id`:
    ortho/COG/log are scope-wide products of one or more datasets fed
    to the same ODM job."""

    def test_no_short_id_segment_even_when_present(self):
        from gemini.workers.odm.worker import _build_output_prefix

        out = _build_output_prefix({
            "year": "2024",
            "experiment": "GEMINI",
            "location": "Davis",
            "population": "Cowpea MAGIC",
            "date": "2024-07-25",
            "platform": "Drone",
            "sensor": "RGB",
            "dataset_short_id": "a2f31b04",
        })
        assert out == "Processed/2024/GEMINI/Davis/Cowpea MAGIC/2024-07-25/Drone/RGB/"


class TestResolveImagePrefixes:
    """`_resolve_image_prefixes` decides which prefix(es) the image
    download walks. Three input shapes:

      - dataset_short_ids list  → one prefix per chosen dataset
      - dataset_short_id str    → exactly one prefix
      - neither                 → scope root (recursive listing picks
                                  up both legacy and new layouts)
    """

    def test_list_form_produces_per_dataset_prefixes(self):
        from gemini.workers.odm.worker import _resolve_image_prefixes

        out = _resolve_image_prefixes({
            "year": "2024",
            "experiment": "GEMINI",
            "date": "2024-07-25",
            "platform": "Drone",
            "sensor": "RGB",
            "dataset_short_ids": ["a2f31b04", "8f1c47de"],
        })
        assert out == [
            "Raw/2024/GEMINI/2024-07-25/Drone/RGB/a2f31b04/Images/",
            "Raw/2024/GEMINI/2024-07-25/Drone/RGB/8f1c47de/Images/",
        ]

    def test_list_form_drops_empty_short_ids(self):
        from gemini.workers.odm.worker import _resolve_image_prefixes

        out = _resolve_image_prefixes({
            "year": "2024",
            "experiment": "GEMINI",
            "date": "2024-07-25",
            "platform": "Drone",
            "sensor": "RGB",
            "dataset_short_ids": ["a2f31b04", "", None],
        })
        assert out == [
            "Raw/2024/GEMINI/2024-07-25/Drone/RGB/a2f31b04/Images/",
        ]

    def test_singular_form_produces_one_prefix(self):
        from gemini.workers.odm.worker import _resolve_image_prefixes

        out = _resolve_image_prefixes({
            "year": "2024",
            "experiment": "GEMINI",
            "date": "2024-07-25",
            "platform": "Drone",
            "sensor": "RGB",
            "dataset_short_id": "a2f31b04",
        })
        assert out == [
            "Raw/2024/GEMINI/2024-07-25/Drone/RGB/a2f31b04/Images/",
        ]

    def test_neither_form_returns_scope_root(self):
        """Legacy / 'all datasets at this scope' fallback. The download
        helper recurses from this prefix, picking up both legacy
        `…/{sensor}/Images/...` and new `…/{sensor}/{shortId}/Images/...`
        files."""
        from gemini.workers.odm.worker import _resolve_image_prefixes

        out = _resolve_image_prefixes({
            "year": "2024",
            "experiment": "GEMINI",
            "date": "2024-07-25",
            "platform": "Drone",
            "sensor": "RGB",
        })
        assert out == ["Raw/2024/GEMINI/2024-07-25/Drone/RGB/"]

    def test_empty_short_ids_list_falls_back_to_scope_root(self):
        """An empty list means the user opened the multi-select but
        deselected everything — treat the same as 'all'."""
        from gemini.workers.odm.worker import _resolve_image_prefixes

        out = _resolve_image_prefixes({
            "year": "2024",
            "experiment": "GEMINI",
            "date": "2024-07-25",
            "platform": "Drone",
            "sensor": "RGB",
            "dataset_short_ids": [],
        })
        assert out == ["Raw/2024/GEMINI/2024-07-25/Drone/RGB/"]
