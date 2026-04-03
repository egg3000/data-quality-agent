#!/bin/bash
set -e

# This script runs inside the Postgres container at startup.
# It creates two databases:
#   1. dqa_app  — application tables (rules, errors, knowledge, conversations)
#   2. dqa_erp  — ERP test data (MARA, MARC, reference tables)
# Then runs the appropriate init scripts against each.

POSTGRES_USER="${POSTGRES_USER:-dqa}"

echo "=== Creating application database: dqa_app ==="
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<-EOSQL
    SELECT 'CREATE DATABASE dqa_app OWNER $POSTGRES_USER'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'dqa_app')\gexec
EOSQL

echo "=== Creating ERP data database: dqa_erp ==="
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<-EOSQL
    SELECT 'CREATE DATABASE dqa_erp OWNER $POSTGRES_USER'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'dqa_erp')\gexec
EOSQL

echo "=== Running app schema init scripts against dqa_app ==="
for f in /docker-entrypoint-initdb.d/app/*.sql; do
    if [ -f "$f" ]; then
        echo "  Running $f ..."
        psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname dqa_app -f "$f"
    fi
done

echo "=== Running ERP test data scripts against dqa_erp ==="
for f in /docker-entrypoint-initdb.d/erp/*.sql; do
    if [ -f "$f" ]; then
        echo "  Running $f ..."
        psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname dqa_erp -f "$f"
    fi
done

echo "=== Database initialization complete ==="
