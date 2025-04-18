#!/bin/bash


echo "The script has started."
# Start Airflow in the background
airflow standalone &

# Wait until Airflow's webserver (port 8080) is available
# while ! nc -z localhost 8080; do
#   sleep 1
# done

# Start socat to forward port 8081 -> 8080
exec socat TCP-LISTEN:8081,fork,reuseaddr TCP:localhost:8080
