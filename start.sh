#!/bin/bash

# Wait for database to be ready
echo "Waiting for database..."
while ! nc -z db 5432; do
  sleep 1
done
echo "Database is up!"

# Wait a bit more to ensure PostgreSQL is ready to accept connections
sleep 5

# Create the database if it doesn't exist using the environment variable
echo "POSTGRES_DB: $POSTGRES_DB"
echo "Creating database $POSTGRES_DB if it doesn't exist..."
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = '$POSTGRES_DB'" | grep -q 1 || PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d postgres -c "CREATE DATABASE $POSTGRES_DB"

# Run migrations with explicit database name from environment
echo "Running migrations..."
PGDATABASE=$POSTGRES_DB 
echo "PGDATABASE: $PGDATABASE"
alembic upgrade head

echo "Migrations complete!"
echo "Starting FastAPI application..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
