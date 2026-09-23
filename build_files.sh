#!/usr/bin/env bash
# Build script for Vercel deployment
set -e
echo "Starting Vercel build process..."

# Install dependencies
python3 -m pip install -r requirements.txt

# Collect static assets for WhiteNoise
python3 manage.py collectstatic --noinput --clear

# Apply database migrations to Neon PostgreSQL
python3 manage.py migrate --noinput

echo "Vercel build completed successfully."
