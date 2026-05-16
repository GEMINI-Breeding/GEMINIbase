"""Pure helpers for the Option-A dataset-path migration.

Lives outside the rest_api package so the unit tests don't transitively
import litestar (the controllers package's __init__.py imports every
controller). The migration controller in
gemini.rest_api.controllers.migrate_dataset_paths re-exports these.
"""
import re

# Matches the per-dataset segment we splice in: 8 lowercase hex chars.
# Must agree with extractDatasetShortId in
# frontend/src/features/files/lib/datasetForUpload.ts.
SHORT_ID_RE = re.compile(r"^[0-9a-f]{8}$")

# Legacy upload key shape, capturing everything up to and including the
# trailing `/Images/{file}`. The new shape inserts `{shortId}/` just
# before the literal `Images/` segment.
LEGACY_KEY_RE = re.compile(r"^(Raw/.+?)/Images/([^/]+)$")


def short_id_from_uuid(uid) -> str | None:
    """First 8 lowercase hex chars of a dataset UUID. None when the
    input is None (FK SET NULL leaves orphan file rows that can't be
    migrated to a per-dataset prefix because there's no dataset)."""
    if uid is None:
        return None
    hex_str = str(uid).replace("-", "").lower()
    if len(hex_str) < 8:
        return None
    return hex_str[:8]


def new_key_for(legacy_key: str, short_id: str) -> str | None:
    """Return the migrated key, or None if the legacy_key isn't in the
    Option-A scope.

    Out-of-scope (returns None):
      - Anything that isn't `Raw/.../Images/{file}` (Processed/...,
        wizard supplemental Raw/{date}/{exp}/file).
      - Already-migrated keys (segment immediately before /Images/ is
        already an 8-hex short-id).
    """
    m = LEGACY_KEY_RE.match(legacy_key)
    if not m:
        return None
    head, filename = m.group(1), m.group(2)
    last_seg = head.rsplit("/", 1)[-1] if "/" in head else head
    if SHORT_ID_RE.match(last_seg):
        return None
    return f"{head}/{short_id}/Images/{filename}"
