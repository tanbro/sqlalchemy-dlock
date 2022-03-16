#!/bin/sh
# wait-for-postgres.sh

set -e

POSTGRES_HOST="$1"
POSTGRES_PASSWORD="$2"
shift

until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -U "postgres" -c '\q'; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 5
done

>&2 echo "Postgres is up!"
