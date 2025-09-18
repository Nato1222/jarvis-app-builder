#!/bin/bash

echo "Starting Jarvis App Builder System..."

echo ""
echo "[1/3] Starting Generator Service..."
cd generator && npm install && npm run dev &
GENERATOR_PID=$!

echo ""
echo "[2/3] Starting Dashboard..."
cd ../dashboard && npm install && npm run dev &
DASHBOARD_PID=$!

echo ""
echo "[3/3] Starting Backend API..."
cd ../JarvisOne && python -m uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

echo ""
echo "All services starting..."
echo "- Generator Service: http://localhost:3001"
echo "- Dashboard: http://localhost:3000"
echo "- Backend API: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop all services"

# Function to cleanup on exit
cleanup() {
    echo "Stopping services..."
    kill $GENERATOR_PID 2>/dev/null
    kill $DASHBOARD_PID 2>/dev/null
    kill $BACKEND_PID 2>/dev/null
    exit
}

# Trap Ctrl+C
trap cleanup INT

# Wait for all background processes
wait
