#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -o errexit

echo "✅ Installing dependencies..."
pip install -r requirements.txt

echo "✅ Applying migrations..."
python manage.py migrate --noinput

echo "✅ Collecting static files..."
python manage.py collectstatic --noinput

echo "✅ Build script completed!"
