#!/bin/bash

echo "🚀 Rebuilding Backend with 4 Uvicorn Workers"
echo "============================================="

# Stop all containers
echo "📦 Stopping existing containers..."
docker-compose down

# Rebuild and start containers
echo "🔨 Building and starting containers..."
docker-compose up --build -d

# Wait a moment for containers to start
echo "⏳ Waiting for containers to start..."
sleep 10

# Show container status
echo "📊 Container Status:"
docker-compose ps

# Show logs for the app container
echo "📝 Backend Logs:"
echo "================"
docker-compose logs app

echo "✅ Backend rebuild complete!"
echo "🌐 Backend available at: http://localhost:8080"
echo "📊 Grafana available at: http://localhost:3000"
echo "🔍 Prometheus available at: http://localhost:9090"
echo ""
echo "📋 To follow logs: docker-compose logs -f app"
echo "🐛 To debug: docker-compose exec app bash" 