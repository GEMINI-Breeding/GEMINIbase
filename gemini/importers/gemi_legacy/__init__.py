"""Import an install of the old GEMI desktop app (v0.0.1–v0.0.5).

The old app kept everything but files in a SQLite database (`gemi.db`) and
its files under a data folder (default ~/GEMI-Data). This package reads
both strictly read-only — the caller mounts them read-only too — and plans
(then performs) the import into GEMINIbase. Nothing is ever written, moved
or deleted in the old install: after an in-place upgrade it is the user's
only way back (merge_plan.md D1).
"""
