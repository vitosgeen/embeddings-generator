#!/bin/bash

# Demo script for Phase 2: Admin UI with HTMX
# This script demonstrates the admin UI functionality via curl

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Phase 2: Admin UI Demo ===${NC}\n"

# Get admin API key
if [ -z "$ADMIN_KEY" ]; then
    echo -e "${YELLOW}Please set ADMIN_KEY environment variable${NC}"
    echo "Example: export ADMIN_KEY='sk-admin-m1YHp13elEvafGYLT27H0gmD'"
    exit 1
fi

BASE_URL="http://localhost:8000"

# Test 1: Check health
echo -e "${GREEN}1. Testing health endpoint...${NC}"
curl -s "$BASE_URL/health" | jq .
echo -e "\n"

# Test 2: Access admin dashboard
echo -e "${GREEN}2. Accessing admin dashboard...${NC}"
response=$(curl -s -H "Authorization: Bearer $ADMIN_KEY" "$BASE_URL/admin/" | grep -o '<title>[^<]*</title>')
echo "Response: $response"
echo -e "\n"

# Test 3: List users
echo -e "${GREEN}3. Listing users...${NC}"
curl -s -H "Authorization: Bearer $ADMIN_KEY" "$BASE_URL/admin/users" | grep -oP '(?<=<td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">).*?(?=</td>)' | head -5
echo -e "\n"

# Test 4: List API keys
echo -e "${GREEN}4. Listing API keys...${NC}"
curl -s -H "Authorization: Bearer $ADMIN_KEY" "$BASE_URL/admin/keys" | grep -oP 'sk-[a-z]+-' | head -3
echo -e "\n"

# Test 5: View audit logs
echo -e "${GREEN}5. Viewing recent audit logs...${NC}"
curl -s -H "Authorization: Bearer $ADMIN_KEY" "$BASE_URL/admin/logs" | grep -oP '(?<=<p class="text-sm font-medium text-gray-900 truncate">).*?(?=</p>)' | head -5
echo -e "\n"

# Test 6: Create a test user (via API - POST form data)
echo -e "${GREEN}6. Creating a test user...${NC}"
curl -s -X POST -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=demo-user&email=demo@example.com&role=monitor" \
  "$BASE_URL/admin/users" | grep -o "demo-user" || echo "User creation attempted (may already exist)"
echo -e "\n"

echo -e "${BLUE}=== Demo Complete ===${NC}"
echo -e "\n${YELLOW}To explore the full UI, open your browser to:${NC}"
echo -e "${YELLOW}$BASE_URL/admin/${NC}"
echo -e "\n${YELLOW}Note: You'll need to configure your browser to send the Authorization header${NC}"
echo -e "${YELLOW}Use browser extensions like ModHeader or Requestly${NC}"
