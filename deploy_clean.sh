#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

# --- CONFIGURATION ---
STACK_NAME="predoc_stack"
OLD_STACK_NAME="predoc-stack"
OLD_SERVICE_NAME="predoc-stack_app"
IMAGE_NAME="predoc-app:latest"
COMPOSE_FILE="docker-compose.yml"

echo "========================================="
echo "🚀 Starting PreDoc-Chatbot Update & Deploy"
echo "========================================="

# 1. Clean up conflicting services/stacks to free up port 8010
echo "🧹 Checking for existing services on port 8010..."

if docker stack ls | grep -q "$OLD_STACK_NAME"; then
    echo "⚠️ Found conflicting stack '$OLD_STACK_NAME'. Removing..."
    sudo docker stack rm "$OLD_STACK_NAME"
    echo "⏳ Waiting 15 seconds for network and port cleanup..."
    sleep 15
fi

if docker service ls | grep -q "$OLD_SERVICE_NAME"; then
    echo "⚠️ Found orphaned service '$OLD_SERVICE_NAME'. Removing..."
    sudo docker service rm "$OLD_SERVICE_NAME"
    echo "⏳ Waiting 10 seconds for ingress port cleanup..."
    sleep 10
fi

# 2. Build the app image using --no-cache
echo "🏗️  Building local Docker image ($IMAGE_NAME) with --no-cache..."
sudo docker build --no-cache -t "$IMAGE_NAME" .

# 3. Deploy the Swarm stack
echo "📦 Deploying Swarm stack '$STACK_NAME'..."
sudo docker stack deploy -c "$COMPOSE_FILE" "$STACK_NAME"

echo "========================================="
echo "✅ Deployment initiated successfully!"
echo "========================================="
echo "Check status using: sudo docker stack services $STACK_NAME"
