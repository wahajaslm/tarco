#!/bin/bash

# Trade Compliance API Startup Script
# This script sets up the environment and starts the API server

set -e

echo "🚀 Starting Trade Compliance API..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies if needed
if [ ! -f "venv/pyvenv.cfg" ]; then
    echo "📥 Installing dependencies..."
    pip install --upgrade pip
    pip install fastapi uvicorn pydantic pydantic-settings sqlalchemy alembic psycopg2-binary redis qdrant-client sentence-transformers jsonschema
fi

# Set Python path
export PYTHONPATH=/Users/wahajaslam/tarco

# Start the server
echo "🌐 Starting API server on http://localhost:8001"
echo "📊 Health check: http://localhost:8001/health"
echo "🔍 API docs: http://localhost:8001/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python api/main.py
