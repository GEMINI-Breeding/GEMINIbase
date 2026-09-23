"""The day-0 schema must be stamped at the newest Alembic revision.

gemini/db/init_sql builds a new database's schema as of the newest
migration and records that revision, so the rest-api can run
`alembic upgrade head` on every start. If a migration is added without
updating the stamp, new installs would re-run it against a schema that
already has it (or skip one it lacks). This keeps them in step.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def alembic_head() -> str:
    revs, downs = set(), set()
    for f in (ROOT / "alembic" / "versions").glob("*.py"):
        text = f.read_text()
        rev = re.search(r'^revision[^=]*=\s*["\']([^"\']+)', text, re.M)
        down = re.search(r'^down_revision[^=]*=\s*["\']([^"\']+)', text, re.M)
        if rev:
            revs.add(rev.group(1))
        if down:
            downs.add(down.group(1))
    heads = revs - downs
    assert len(heads) == 1, f"expected one Alembic head, found {sorted(heads)}"
    return heads.pop()


def stamp(path: Path) -> str:
    m = re.search(r"INSERT INTO gemini\.alembic_version \(version_num\) VALUES \('([^']+)'\)",
                  path.read_text())
    assert m, f"{path} doesn't stamp gemini.alembic_version"
    return m.group(1)


def test_day0_schema_is_stamped_at_head():
    head = alembic_head()
    assert stamp(ROOT / "gemini/db/init_sql/scripts/7_alembic_version.sql") == head
    assert stamp(ROOT / "tests/init_sql/01_init.sql") == head
