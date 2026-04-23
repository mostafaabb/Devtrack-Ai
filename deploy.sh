#!/bin/bash

# ══════════════════════════════════════════════════════════════════
# DevTrack AI - Production Deployment & Management Script
# ══════════════════════════════════════════════════════════════════

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Beginning DevTrack AI Production Setup...${NC}"

# Function: Generate Secure Secret
generate_secret() {
    python3 -c "import secrets; print(secrets.token_hex(32))"
}

# 1. Check/Generate .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  No .env file found. Generating from production template...${NC}"
    cp .env.production .env
    
    # Generate random secrets
    SECRET_KEY=$(generate_secret)
    JWT_SECRET_KEY=$(generate_secret)
    DB_PASSWORD=$(generate_secret)
    
    # Update .env
    sed -i "s/CHANGE_ME_GENERATE_A_SECURE_64_CHAR_HEX_STRING/$SECRET_KEY/g" .env
    sed -i "s/CHANGE_ME_GENERATE_A_SECURE_64_CHAR_HEX_STRING/$JWT_SECRET_KEY/g" .env
    sed -i "s/CHANGE_ME_STRONG_DATABASE_PASSWORD/$DB_PASSWORD/g" .env
    
    echo -e "${GREEN}✅ .env file created with secure generated secrets.${NC}"
    echo -e "${YELLOW}👉 IMPORTANT: Manually add your GEMINI_API_KEY to the .env file!${NC}"
fi

# 2. Setup SSL Certificate Directory
mkdir -p nginx/ssl
if [ ! -f nginx/ssl/cert.pem ]; then
    echo -e "${YELLOW}⚠️  No SSL certificates found. Generating self-signed cert for testing...${NC}"
    openssl req -x509 -newkey rsa:4096 -nodes \
        -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem -days 365 \
        -subj '/CN=localhost'
    echo -e "${GREEN}✅ Self-signed SSL certificates generated.${NC}"
fi

# 3. Start Infrastructure Stack
echo -e "${BLUE}🐳 Starting Docker Compose stack (Production mode)...${NC}"
docker-compose -f docker-compose.prod.yml up -d --build

# 4. Run Database Migrations
echo -e "${BLUE}🗄️  Running database migrations...${NC}"
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

# 5. Check Health
echo -e "${BLUE}📡 Checking system health...${NC}"
sleep 10
HEALTH=$(curl -s http://localhost/api/health)

if [[ $HEALTH == *"healthy"* ]]; then
    echo -e "${GREEN}✅ SYSTEM IS ONLINE AND HEALTHY!${NC}"
    echo -e "   - Dashboard: https://localhost"
    echo -e "   - API Docs: https://localhost/api/docs"
else
    echo -e "${RED}❌ Health check failed. Check logs with: docker-compose logs api${NC}"
fi

echo -e "${BLUE}Done!${NC}"
