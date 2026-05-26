#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}"
echo "  ╔══════════════════════════╗"
echo "  ║  FacTisa Ultra Installer  ║"
echo "  ╚══════════════════════════╝"
echo -e "${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Installing Docker...${NC}"
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker && systemctl start docker
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${YELLOW}Installing Docker Compose...${NC}"
    apt-get install -y docker-compose-plugin 2>/dev/null || pip install docker-compose
fi

# Setup .env
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠️  .env ساخته شد. لطفاً مقادیر را تنظیم کنید:${NC}"
    echo ""
    read -p "🤖 BOT_TOKEN: " BOT_TOKEN
    read -p "👤 ADMIN_IDS (comma-separated): " ADMIN_IDS
    read -p "🏢 COMPANY_NAME: " COMPANY_NAME
    read -p "📞 COMPANY_PHONE: " COMPANY_PHONE
    DB_PASS=$(openssl rand -hex 16)
    sed -i "s/your_bot_token_here/$BOT_TOKEN/" .env
    sed -i "s/123456789,987654321/$ADMIN_IDS/" .env
    sed -i "s/شرکت من/$COMPANY_NAME/" .env
    sed -i "s/09123456789/$COMPANY_PHONE/" .env
    sed -i "s/ultra_secret/$DB_PASS/g" .env
    echo -e "${GREEN}✅ .env تنظیم شد${NC}"
fi

# Create fonts dir
mkdir -p fonts
if [ ! -f fonts/Vazir.ttf ]; then
    echo -e "${YELLOW}Downloading Vazir font...${NC}"
    curl -sL "https://github.com/rastikerdar/vazir-font/releases/download/v30.1.0/Vazir.ttf" -o fonts/Vazir.ttf 2>/dev/null || echo -e "${YELLOW}Font download failed - PDF will use default font${NC}"
    curl -sL "https://github.com/rastikerdar/vazir-font/releases/download/v30.1.0/Vazir-Bold.ttf" -o fonts/Vazir-Bold.ttf 2>/dev/null || true
fi

# Build & start
echo -e "${GREEN}Building and starting containers...${NC}"
docker compose up -d --build 2>/dev/null || docker-compose up -d --build

echo ""
echo -e "${GREEN}╔══════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ FacTisa Ultra is running!  ║${NC}"
echo -e "${GREEN}╚══════════════════════════╝${NC}"
echo ""
echo "  docker compose logs -f bot    # view logs"
echo "  docker compose down           # stop"
echo "  docker compose restart bot    # restart"
echo ""
