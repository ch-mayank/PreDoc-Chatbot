#!/usr/bin/env bash
# ==============================================================================
# PreDoc AI: Automated Docker Swarm Zero-Downtime Stack Deployment Script
# Target: Full-Stack AI Solutions Founder / Solo Architect
# Usage: ./deploy_stack.sh [stack_name]
# ==============================================================================

set -euo pipefail

STACK_NAME="${1:-predoc_beta}"
SECRETS_DIR="/mnt/data/work/work-secrets"
COMPOSE_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/docker-compose.swarm.yml"

echo "=== [PreDoc AI] Initiating Swarm Deployment: ${STACK_NAME} ==="

# 1. Verify Swarm Manager State
if ! docker info --format '{{.Swarm.LocalNodeState}}' | grep -q "active"; then
    echo "[!] Docker Swarm not active. Initializing single-node Swarm manager..."
    docker swarm init || true
fi

# 2. Provision Swarm Secrets from Secure Host Work-Secrets
echo "--> Provisioning cryptographic Swarm secrets..."
provision_secret() {
    local secret_name="$1"
    local secret_file="${SECRETS_DIR}/${secret_name}"
    
    if [ ! -f "${secret_file}" ] && [ -f "${secret_file}.txt" ]; then
        secret_file="${secret_file}.txt"
    fi

    if [ -f "${secret_file}" ]; then
        if docker secret inspect "${secret_name}" >/dev/null 2>&1; then
            echo "    [i] Secret '${secret_name}' already exists in Swarm."
        else
            echo "    [+] Registering secret '${secret_name}' into Swarm..."
            docker secret create "${secret_name}" "${secret_file}"
        fi
    else
        echo "    [!] Warning: Secret file '${secret_file}' not found. Skipping."
    fi
}

provision_secret "primary_api_key"
provision_secret "nvidia_api_key"
provision_secret "openrouter_key"
provision_secret "admin_user"
provision_secret "admin_pass"
provision_secret "clinical_api_key"
provision_secret "admin_api_key"

# 3. Deploy Multi-Container Stack
echo "--> Deploying stack '${STACK_NAME}' via ${COMPOSE_FILE}..."
docker stack deploy -c "${COMPOSE_FILE}" "${STACK_NAME}" --with-registry-auth

# 4. Monitor Rolling Deployment
echo "--> Verifying service rollout status..."
docker stack services "${STACK_NAME}"

echo "=== [PreDoc AI] Stack '${STACK_NAME}' deployed successfully ==="
