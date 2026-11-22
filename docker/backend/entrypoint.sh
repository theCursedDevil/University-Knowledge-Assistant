#!/bin/bash
set -e

echo "[BACKEND ENTRYPOINT] Checking PostgreSQL Primary connectivity..."
max_retries=30
count=0
until python -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2.0)
s.connect(('${POSTGRES_HOST:-postgres-primary}', int('${POSTGRES_PORT:-5432}')))
s.close()
" 2>/dev/null || [ $count -ge $max_retries ]; do
    echo "[BACKEND ENTRYPOINT] Waiting for database at ${POSTGRES_HOST:-postgres-primary}:${POSTGRES_PORT:-5432} (attempt $((count+1))/$max_retries)..."
    sleep 2
    count=$((count+1))
done

if [ $count -ge $max_retries ]; then
    echo "[BACKEND ENTRYPOINT] ERROR: Timed out waiting for PostgreSQL Primary!"
    exit 1
fi

echo "[BACKEND ENTRYPOINT] PostgreSQL Primary is ready. Running database migrations (alembic upgrade head)..."
alembic upgrade head || {
    echo "[BACKEND ENTRYPOINT] Note: Alembic upgrade finished with status $?."
}

echo "[BACKEND ENTRYPOINT] Executing command: $@"
exec "$@"
