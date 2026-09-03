#!/usr/bin/env bash
set -e

STACK_NAME="predoc_stack"
IMAGE_NAME="predoc-app:latest"

echo "🔄 Rebuilding image with your latest file changes..."
#sudo docker build --no-cache -t "$IMAGE_NAME" .
sudo docker build -t "$IMAGE_NAME" .

echo "🚀 Rolling out file updates to Swarm..."
sudo docker service update --image "$IMAGE_NAME" --force "${STACK_NAME}_app"

echo "✅ Update complete! Swarm is restarting the container with your new files."