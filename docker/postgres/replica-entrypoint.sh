#!/bin/sh
set -e

PRIMARY_HOST="${PRIMARY_HOST:-postgres-primary}"
PRIMARY_PORT="${PRIMARY_PORT:-5432}"
PRIMARY_USER="${PRIMARY_USER:-postgres}"
REPL_USER="${REPL_USER:-uka_replicator}"
REPL_PASSWORD="${REPL_PASSWORD:-uka_replica_stream_password}"
REPL_SLOT="${REPL_SLOT:-replica_1_slot}"
PGDATA="${PGDATA:-/var/lib/postgresql/data}"

echo "Starting standby replica configuration for slot: $REPL_SLOT..."

# If PGDATA does not contain a PostgreSQL data directory, take a base backup from the primary
if [ ! -s "$PGDATA/PG_VERSION" ]; then
    echo "Standby database directory is empty. Waiting for primary $PRIMARY_HOST:$PRIMARY_PORT..."
    until pg_isready -h "$PRIMARY_HOST" -p "$PRIMARY_PORT" -U "$PRIMARY_USER"; do
        echo "Primary not ready yet, sleeping 1s..."
        sleep 1
    done

    echo "Primary is ready. Taking pg_basebackup from $PRIMARY_HOST using replication slot $REPL_SLOT..."
    rm -rf "${PGDATA:?}"/*
    PGPASSWORD="$REPL_PASSWORD" pg_basebackup \
        -h "$PRIMARY_HOST" \
        -p "$PRIMARY_PORT" \
        -U "$REPL_USER" \
        -D "$PGDATA" \
        -Fp \
        -Xs \
        -P \
        -R \
        -S "$REPL_SLOT"

    echo "Base backup completed successfully."
fi

# Ensure standby.signal exists for PostgreSQL 16
touch "$PGDATA/standby.signal"

chown -R postgres:postgres "$PGDATA"
chmod 700 "$PGDATA"

echo "Starting PostgreSQL 16 as user 'postgres' in read-only standby mode..."
if command -v gosu >/dev/null 2>&1; then
    exec gosu postgres postgres -c hot_standby=on -c default_transaction_read_only=on
elif command -v su-exec >/dev/null 2>&1; then
    exec su-exec postgres postgres -c hot_standby=on -c default_transaction_read_only=on
else
    exec su -s /bin/sh postgres -c "postgres -c hot_standby=on -c default_transaction_read_only=on"
fi
