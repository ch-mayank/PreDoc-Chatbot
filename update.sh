#!/usr/bin/env bash
# ==============================================================================
# PreDoc Production Swarm Update Script
# Usage: ./update.sh [--no-cache]
# ==============================================================================
set -e

STACK_NAME="predoc_stack"
IMAGE_NAME="predoc-app:latest"
HEALTH_URL="http://127.0.0.1:8010/health"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

BUILD_ARGS=""
if [[ "$1" == "--no-cache" ]]; then
    BUILD_ARGS="--no-cache"
    echo -e "${YELLOW}⚡ Building Docker image with --no-cache...${NC}"
fi

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}🚀 PreDoc-Chatbot Swarm Rolling Update${NC}"
echo -e "${BLUE}=========================================${NC}"

# 1. Build the updated image
echo -e "\n${BLUE}🏗️  Step 1: Building Docker image ($IMAGE_NAME)...${NC}"
sudo docker build $BUILD_ARGS -t "$IMAGE_NAME" .

# 2. Roll out to Docker Swarm
echo -e "\n${BLUE}🚀 Step 2: Rolling out update to Docker Swarm service '${STACK_NAME}_app'...${NC}"
sudo docker service update --image "$IMAGE_NAME" --force "${STACK_NAME}_app"

# 3. Health Check Verification
echo -e "\n${BLUE}🩺 Step 3: Verifying service health ($HEALTH_URL)...${NC}"
MAX_RETRIES=15
WAIT_SECONDS=2
PASSED=false

for ((i=1; i<=MAX_RETRIES; i++)); do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" || true)
    if [[ "$HTTP_CODE" == "200" ]]; then
        PASSED=true
        break
    fi
    echo -e "${YELLOW}⏳ Waiting for service to report healthy (attempt $i/$MAX_RETRIES, code: $HTTP_CODE)...${NC}"
    sleep "$WAIT_SECONDS"
done

if [[ "$PASSED" == "true" ]]; then
    echo -e "${GREEN}✅ Health check passed! Service is live and healthy.${NC}"
    curl -s "$HEALTH_URL" | grep -o '"status":"[^"]*"' || true
    echo ""
else
    echo -e "${RED}⚠️ Warning: Health check did not return 200 within timeout.${NC}"
    echo -e "Inspect logs with: sudo docker service logs --tail 30 ${STACK_NAME}_app"
fi

# 4. Display Tunnel URL if running
TUNNEL_URL=$(sudo docker service logs --tail 50 ${STACK_NAME}_tunnel 2>&1 | grep -o 'https://[a-zA-Z0-9.-]*\.trycloudflare\.com' | tail -n 1 || true)
if [[ -n "$TUNNEL_URL" ]]; then
    echo -e "${GREEN}🌐 Public Cloudflare Tunnel:${NC} $TUNNEL_URL"
fi

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}🎉 Update & rollout completed successfully!${NC}"
echo -e "${GREEN}=========================================${NC}"