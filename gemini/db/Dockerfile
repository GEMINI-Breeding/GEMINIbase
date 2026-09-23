# Official PostgreSQL 16 image (Debian-based, supports apt-get for building extensions)
FROM postgres:16

USER root

# Install Dependencies
RUN apt-get update && apt-get install -y \
    lsb-release \
    gcc \
    make \
    libssl-dev \
    autoconf \
    pkg-config \
    libcurl4-gnutls-dev \
    liblz4-dev \
    libzstd-dev \
    git \
    postgresql-server-dev-16

# Copy setup script to PostgreSQL's pre-initialization directory
COPY ./setup.sh /scripts/setup.sh
RUN chmod +x /scripts/setup.sh

# Run the setup script
RUN /scripts/setup.sh

# Copy SQL scripts to initialize the database
COPY ./init_sql /docker-entrypoint-initdb.d/

# No `USER postgres` here: the official entrypoint starts as root, makes
# the data directory the postgres user's, then drops to postgres itself.
# Starting as postgres broke host-folder data directories on Linux
# ("could not change permissions of directory"), which the desktop app
# uses (GEMINI_DATA_DIR/postgres).
