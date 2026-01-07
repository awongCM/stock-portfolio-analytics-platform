#!/bin/bash
# Verification script for renamed repository

set -e

echo "================================"
echo "Repository Rename Verification"
echo "================================"
echo ""

echo "✓ Directory: stock-portfolio-analytics-platform"
echo "✓ Location: $(pwd)"
echo ""

echo "Checking updated files..."
echo ""

# Check pyproject.toml
if grep -q "stock-portfolio-analytics-platform" pyproject.toml; then
    echo "✓ pyproject.toml updated correctly"
else
    echo "✗ pyproject.toml not updated"
    exit 1
fi

# Check README.md
if grep -q "Stock Portfolio Analytics Platform" README.md; then
    echo "✓ README.md updated correctly"
else
    echo "✗ README.md not updated"
    exit 1
fi

# Check DEMO_RESULTS.md
if grep -q "Stock Portfolio Analytics Platform" DEMO_RESULTS.md; then
    echo "✓ DEMO_RESULTS.md updated correctly"
else
    echo "✗ DEMO_RESULTS.md not updated"
    exit 1
fi

echo ""
echo "Verifying Poetry configuration..."
poetry check

echo ""
echo "================================"
echo "✅ All checks passed!"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Update git remote if needed"
echo "2. Run: poetry install (to update lock file)"
echo "3. Run: ./scripts/start-services.sh (to test services)"
echo "4. Run: poetry run pytest (to run tests)"
