#!/bin/bash
set -e

echo "Configuring PostgreSQL Primary for physical streaming replication..."

# Append host replication entry to pg_hba.conf if not already present
if ! grep -q "host replication all 0.0.0.0/0 scram-sha-256" "$PGDATA/pg_hba.conf"; then
    echo "host replication all 0.0.0.0/0 scram-sha-256" >> "$PGDATA/pg_hba.conf"
    echo "Replication pg_hba entry added."
fi
