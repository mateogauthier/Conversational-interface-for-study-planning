#!/bin/bash
# Validation script to check line endings in Docker-related files
# This helps prevent build failures on Windows due to CRLF line endings

set -e

echo "=================================================="
echo "Docker Files Line Ending Validator"
echo "=================================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track if any issues were found
ISSUES_FOUND=0

# Function to check file line endings
check_file() {
    local file=$1

    if [ ! -f "$file" ]; then
        echo -e "${YELLOW}⚠ SKIP${NC}: $file (file not found)"
        return
    fi

    # Check for CRLF line endings
    if file "$file" | grep -q "CRLF"; then
        echo -e "${RED}✗ FAIL${NC}: $file has Windows (CRLF) line endings"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    else
        echo -e "${GREEN}✓ PASS${NC}: $file has correct (LF) line endings"
    fi
}

echo "Checking critical Docker files..."
echo ""

# Change to the CODE directory
cd "$(dirname "$0")/.." || exit 1

# Check all shell scripts
echo "=== Shell Scripts ==="
for script in scripts/*.sh; do
    check_file "$script"
done
echo ""

# Check Dockerfiles
echo "=== Docker Configuration ==="
check_file "Dockerfile"
check_file "../docker-compose.yml"
check_file "../docker-compose.prod.yml"
echo ""

# Summary
echo "=================================================="
if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}✓ All files have correct line endings!${NC}"
    echo ""
    echo "You can safely run: docker compose up"
    exit 0
else
    echo -e "${RED}✗ Found $ISSUES_FOUND file(s) with incorrect line endings${NC}"
    echo ""
    echo "To fix these issues, run ONE of the following:"
    echo ""
    echo "Option 1 - Fix individual files with dos2unix:"
    echo "  dos2unix CODE/scripts/*.sh"
    echo ""
    echo "Option 2 - Re-clone the repository with correct Git settings:"
    echo "  git config --global core.autocrlf false"
    echo "  git rm --cached -r ."
    echo "  git reset --hard"
    echo ""
    echo "Option 3 - Let Docker handle it (already configured in Dockerfile)"
    echo "  docker compose up --build"
    echo "  (The build process will automatically fix line endings)"
    echo ""
    exit 1
fi
