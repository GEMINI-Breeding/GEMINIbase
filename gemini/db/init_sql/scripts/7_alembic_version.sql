-- Record which Alembic revision this day-0 schema corresponds to.
--
-- The scripts above build the schema as of the newest migration, so a new
-- database is already "at head". Stamping it here lets the rest-api run
-- `alembic upgrade head` on every start (GEMINI_RUN_MIGRATIONS=1) without a
-- manual `alembic stamp` on day 0, while a database built by an OLDER
-- release keeps its own, older stamp and gets upgraded.
--
-- Keep this in step with alembic/versions: when adding a migration, also
-- change the init scripts AND this revision. A unit test
-- (tests/unit/db/test_init_sql_alembic_stamp.py) fails CI if they disagree.
CREATE TABLE IF NOT EXISTS gemini.alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
INSERT INTO gemini.alembic_version (version_num) VALUES ('0011_process_entities');
