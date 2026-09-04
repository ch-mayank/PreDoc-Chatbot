#!/usr/bin/env bash
# ==============================================================================
# PreDoc Production Swarm Clean Deployment Script
# Usage: ./deploy_clean.sh [--no-cache]
# ==============================================================================
set -e

STACK_NAME="predoc_stack"
OLD_STACK_NAME="predoc-stack"
OLD_SERVICE_NAME="predoc-stack_app"
IMAGE_NAME="predoc-app:latest"
COMPOSE_FILE="docker-compose.yml"
HEALTH_URL="http://127.0.0.1:8010/health"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

BUILD_ARGS=""
if [[ "$1" == "--no-cache" ]]; then
    BUILD_ARGS="--no-cache"
fi

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}🚀 PreDoc-Chatbot Clean Deployment${NC}"
echo -e "${BLUE}=========================================${NC}"

# 1. Verify required Docker secrets
echo -e "\n${BLUE}🔐 Step 1: Verifying Docker Swarm secrets...${NC}"
REQUIRED_SECRETS=("openrouter_key" "admin_user" "admin_pass" "demo_api_key")
EXISTING_SECRETS=$(sudo docker secret ls --format "{{.Name}}")

MISSING_SECRETS=()
for sec in "${REQUIRED_SECRETS[@]}"; do
    if ! echo "$EXISTING_SECRETS" | grep -qx "$sec"; then
        MISSING_SECRETS+=("$sec")
    fi
done

if [[ ${#MISSING_SECRETS[@]} -gt 0 ]]; then
    echo -e "${RED}❌ Missing required Docker secrets: ${MISSING_SECRETS[*]}${NC}"
    echo -e "Create missing secrets with: echo 'secret_value' | sudo docker secret create <name> -"
    exit 1
fi
echo -e "${GREEN}✅ All required secrets present.${NC}"

# 2. Cleanup orphaned services and stacks
echo -e "\n${BLUE}🧹 Step 2: Cleaning up obsolete/conflicting services on port 8010...${NC}"
if sudo docker stack ls | grep -q "$OLD_STACK_NAME"; then
    echo -e "${YELLOW}⚠️ Found conflicting stack '$OLD_STACK_NAME'. Removing...${NC}"
    sudo docker stack rm "$OLD_STACK_NAME"
    sleep 10
fi

if sudo docker service ls | grep -q "$OLD_SERVICE_NAME"; then
    echo -e "${YELLOW}⚠️ Found orphaned service '$OLD_SERVICE_NAME'. Removing...${NC}"
    sudo docker service rm "$OLD_SERVICE_NAME"
    sleep 5
fi

# 3. Build image
echo -e "\n${BLUE}🏗️  Step 3: Building Docker image ($IMAGE_NAME)...${NC}"
sudo docker build $BUILD_ARGS -t "$IMAGE_NAME" .

# 4. Deploy Swarm Stack
echo -e "\n${BLUE}📦 Step 4: Deploying Swarm stack '$STACK_NAME'...${NC}"
sudo docker stack deploy -c "$COMPOSE_FILE" "$STACK_NAME"

# 5. Verify Health Check
echo -e "\n${BLUE}🩺 Step 5: Awaiting service health on $HEALTH_URL...${NC}"
MAX_RETRIES=20
WAIT_SECONDS=3
PASSED=false

for ((i=1; i<=MAX_RETRIES; i++)); do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" || true)
    if [[ "$HTTP_CODE" == "200" ]]; then
        PASSED=true
        break
    fi
    echo -e "${YELLOW}⏳ Waiting for app container startup (attempt $i/$MAX_RETRIES, code: $HTTP_CODE)...${NC}"
    sleep "$WAIT_SECONDS"
done

if [[ "$PASSED" == "true" ]]; then
    echo -e "${GREEN}✅ App is live and healthy!${NC}"
    curl -s "$HEALTH_URL"
    echo ""
else
    echo -e "${RED}⚠️ Warning: Service did not report healthy within expected window.${NC}"
    echo -e "Check status: sudo docker stack ps $STACK_NAME"
    echo -e "Check logs: sudo docker service logs --tail 40 ${STACK_NAME}_app"
fi

# 6. Public Tunnel Detection
sleep 3
TUNNEL_URL=$(sudo docker service logs --tail 50 ${STACK_NAME}_tunnel 2>&1 | grep -o 'https://[a-zA-Z0-9.-]*\.trycloudflare\.com' | tail -n 1 || true)
if [[ -n "$TUNNEL_URL" ]]; then
    echo -e "\n${GREEN}🌐 Public Cloudflare URL:${NC} $TUNNEL_URL"
fi

echo -e "\n${GREEN}=========================================${NC}"
echo -e "${GREEN}🎉 Clean Deployment completed successfully!${NC}"
echo -e "${GREEN}=========================================${NC}"
