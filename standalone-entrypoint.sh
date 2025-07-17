#!/bin/bash

echo "The script has started."

if ! curl -s --head --max-time 5 https://google.com >/dev/null; then
  echo "No internet connectivity detected. Exiting script."
  exit 1
fi

# Wait for PostgreSQL to be ready
until pg_isready -h airflow-postgres -p 5432 -U airflow; do
  echo "Waiting for PostgreSQL..."
  sleep 1
done

export PYTHONPATH=$PYTHONPATH:/app

# Initialize the database
airflow db init

# Create admin user if it doesn't exist
AIRFLOW_USERNAME=admin
if [ -z "${AIRFLOW_PASSWORD}" ]; then
  echo "Error: AIRFLOW_PASSWORD environment variable is not set." >&2
  exit 1
fi
if ! airflow users list | grep -q "^${AIRFLOW_USERNAME} "; then
  airflow users create \
    --username "$AIRFLOW_USERNAME" \
    --password "$AIRFLOW_PASSWORD" \
    --firstname First \
    --lastname Last \
    --role Admin \
    --email admin@example.com
fi

# Start Airflow components in the background
airflow webserver &
airflow scheduler &
airflow celery worker &

# Start socat in the foreground to maintain container lifetime
exec socat TCP-LISTEN:8081,fork,reuseaddr TCP:localhost:8080
