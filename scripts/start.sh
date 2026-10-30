#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p logs evidence
if [ ! -s certs/ca.pem ]; then sh scripts/certs.sh >logs/certs.log 2>&1; fi
python manage.py check
nginx -t -p "$(pwd)/" -c nginx.conf
bin/dice-server >logs/server.log 2>&1 &
server_pid=$!
nginx -p "$(pwd)/" -c nginx.conf -g 'daemon off;' >logs/nginx.log 2>&1 &
nginx_pid=$!
python manage.py runserver 0.0.0.0:8000 --noreload >logs/django-8000.log 2>&1 &
client_a=$!
python manage.py runserver 0.0.0.0:8001 --noreload >logs/django-8001.log 2>&1 &
client_b=$!
trap 'kill "$client_a" "$client_b" "$nginx_pid" "$server_pid" 2>/dev/null || true; wait' INT TERM EXIT
wait "$server_pid"
