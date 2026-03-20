#!/bin/bash
# Test script for RedClaw Docker image variants

set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     RedClaw Docker Image Variant Testing                 ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Test target (Google's DNS - safe to test)
TARGET="8.8.8.8"

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

test_image() {
    local variant=$1
    local expected_tools=$2

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${YELLOW}Testing: redclaw/kali:${variant}${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Check if image exists
    if ! docker images | grep -q "redclaw/kali.*${variant}"; then
        echo -e "${RED}✗ Image not found: redclaw/kali:${variant}${NC}"
        echo "  Build it with: cd docker && make build-${variant}"
        return 1
    fi

    # Get image size
    size=$(docker images redclaw/kali:${variant} --format "{{.Size}}")
    echo -e "📦 Image size: ${GREEN}${size}${NC}"

    # Test basic tool availability
    echo ""
    echo "Testing tool availability:"

    for tool in ${expected_tools}; do
        if docker run --rm redclaw/kali:${variant} which ${tool} > /dev/null 2>&1; then
            echo -e "  ${GREEN}✓${NC} ${tool}"
        else
            echo -e "  ${RED}✗${NC} ${tool} (not found)"
        fi
    done

    # Quick nmap test (all variants have nmap)
    echo ""
    echo "Running quick nmap test on ${TARGET}..."
    if docker run --rm redclaw/kali:${variant} nmap -sn ${TARGET} 2>&1 | grep -q "Host is up"; then
        echo -e "  ${GREEN}✓ nmap test passed${NC}"
    else
        echo -e "  ${YELLOW}⚠ nmap test inconclusive (host may be down)${NC}"
    fi

    echo ""
}

# Test minimal variant
echo ""
test_image "minimal" "nmap dig whois"

# Test standard variant
echo ""
test_image "standard" "nmap dig whois nikto gobuster"

# Test full variant
echo ""
test_image "full" "nmap dig whois nikto gobuster nuclei"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✓ Testing complete!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Summary:"
docker images | grep redclaw/kali | awk '{printf "  %-30s %s\n", $1":"$2, $7" "$8}'
echo ""
