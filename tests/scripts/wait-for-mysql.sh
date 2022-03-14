#!/bin/sh
# wait-for-postgres.sh

set -e

MYSQL_HOST="$1"
MYSQL_DATABASE="$2"
MYSQL_USER="$3"
MYSQL_PASSWORD="$4"
shift

until mysql -u "$MYSQL_USER" --password="$MYSQL_PASSWORD" -h "$MYSQL_HOST" -e "use $MYSQL_DATABASE" ; do
  >&2 echo "MySQL is unavailable - sleeping"
  sleep 5
done

>&2 echo "MySQL is up!"
