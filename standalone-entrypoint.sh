#!/bin/bash

#!/bin/bash
echo "The script has started."

# Wait for PostgreSQL to be ready
until pg_isready -h airflow-postgres -p 5432 -U airflow; do
  echo "Waiting for PostgreSQL..."
  sleep 1
done

# Wait for Redis to be ready
until redis-cli -h redis -p 6379 ping; do
  echo "Waiting for Redis..."
  sleep 1
done

# Initialize the database
airflow db init

# Create admin user if it doesn't exist
AIRFLOW_USERNAME=admin
AIRFLOW_PASSWORD=admin
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

