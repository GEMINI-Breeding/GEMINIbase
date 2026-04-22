#!/bin/bash

# Exit on error
set -e

# Check if POSTGRES_DB environment variable is set
if [ -z "${POSTGRESQL_DATABASE}" ]; then
    echo "Error: POSTGRES_DB environment variable is not set"
    exit 1
fi

echo "Database created successfully"

# Check if POSTGRESQL_USERNAME environment variable is set
if [ -z "${POSTGRESQL_USERNAME}" ]; then
    echo "Error: POSTGRESQL_USERNAME environment variable is not set"
    exit 1
fi

# Check if POSTGRESQL_PASSWORD environment variable is set
if [ -z "${POSTGRESQL_PASSWORD}" ]; then
    echo "Error: POSTGRESQL_PASSWORD environment variable is not set"
    exit 1
fi

# Check if POSTGRESQL_DATABASE environment variable is set
if [ -z "${POSTGRESQL_DATABASE}" ]; then
    echo "Error: POSTGRESQL_DATABASE environment variable is not set"
    exit 1
fi

# docker-entrypoint sources this script while postgres is already running on
# the Unix socket at /var/run/postgresql — connect via peer auth over the
# socket (no host/port), using the superuser created by POSTGRES_USER.
PSQL=(psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB")

"${PSQL[@]}" <<EOSQL
    -- Create a schema for the GEMINI Database
    CREATE SCHEMA IF NOT EXISTS gemini;

    -- Initialize Extensions
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; -- Used for generating UUIDs
    CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- Used for generating passwords
    CREATE EXTENSION IF NOT EXISTS columnar;    -- Used for columnar storage
    CREATE EXTENSION IF NOT EXISTS pg_ivm;

    -- Set default table access method
    ALTER DATABASE $POSTGRESQL_DATABASE SET default_table_access_method = 'heap';

    -- Grant Permissions
    GRANT ALL PRIVILEGES ON SCHEMA gemini TO $POSTGRESQL_USERNAME;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA gemini TO $POSTGRESQL_USERNAME;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA gemini TO $POSTGRESQL_USERNAME;
    GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA gemini TO $POSTGRESQL_USERNAME;
    GRANT ALL PRIVILEGES ON DATABASE $POSTGRESQL_DATABASE TO $POSTGRESQL_USERNAME;
EOSQL

echo "Database initialization completed successfully"

# Run the rest of the SQL scripts (schema, views, functions, seed data)
for f in /docker-entrypoint-initdb.d/scripts/*.sql; do
    echo "Running $f"
    "${PSQL[@]}" -f "$f"
done