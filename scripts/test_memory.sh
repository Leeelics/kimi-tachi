#!/bin/bash
# Quick memory integration test script

set -e  # Exit on error

echo "🧠 Kimi-Tachi Memory Integration Test"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((TESTS_PASSED++))
}

fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    ((TESTS_FAILED++))
}

warn() {
    echo -e "${YELLOW}⚠ WARN${NC}: $1"
}

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "Error: Please run from kimi-tachi root directory"
    exit 1
fi

echo "Step 1: Checking dependencies..."
echo "-----------------------------------"

# Check kimi-tachi
if command -v kimi-tachi &> /dev/null; then
    VERSION=$(kimi-tachi --version 2>&1)
    pass "kimi-tachi installed: $VERSION"
else
    fail "kimi-tachi not installed"
    echo "Run: pip install -e ."
    exit 1
fi

# Check memnexus
if python3 -c "import memnexus" 2>/dev/null; then
    pass "memnexus available"
else
    fail "memnexus not installed"
    echo "Run: pip install memnexus"
    exit 1
fi

echo ""
echo "Step 2: Setting up test project..."
echo "-----------------------------------"

TEST_DIR="/tmp/kimi-tachi-memory-test-$$"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

# Initialize git
git init > /dev/null 2>&1

# Create test files
cat > auth.py << 'EOF'
"""Authentication module."""
class AuthManager:
    def authenticate(self, username: str, password: str):
        """Authenticate user."""
        pass
    
    def generate_token(self, user_id: str) -> str:
        """Generate JWT token."""
        return f"token_{user_id}"
EOF

cat > models.py << 'EOF'
"""Data models."""
class User:
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name
EOF

git add . > /dev/null 2>&1
git commit -m "Initial commit" > /dev/null 2>&1

pass "Test project created at $TEST_DIR"

echo ""
echo "Step 3: Testing memory init..."
echo "-----------------------------------"

if kimi-tachi memory init > /dev/null 2>&1; then
    pass "Memory initialized"
else
    fail "Memory init failed"
fi

echo ""
echo "Step 4: Testing memory index..."
echo "-----------------------------------"

INDEX_OUTPUT=$(kimi-tachi memory index 2>&1)
if echo "$INDEX_OUTPUT" | grep -q "Indexed"; then
    GIT_COMMITS=$(echo "$INDEX_OUTPUT" | grep "Git commits" | grep -o '[0-9]\+')
    CODE_SYMBOLS=$(echo "$INDEX_OUTPUT" | grep "Code symbols" | grep -o '[0-9]\+')
    pass "Indexing complete (Git: $GIT_COMMITS, Code: $CODE_SYMBOLS)"
else
    fail "Indexing failed"
    echo "$INDEX_OUTPUT"
fi

echo ""
echo "Step 5: Testing memory search..."
echo "-----------------------------------"

SEARCH_OUTPUT=$(kimi-tachi memory search "authentication" 2>&1)
if echo "$SEARCH_OUTPUT" | grep -q "auth.py\|authenticate"; then
    pass "Search found relevant results"
else
    warn "Search may not have found expected results"
    echo "$SEARCH_OUTPUT"
fi

echo ""
echo "Step 6: Testing incremental indexing..."
echo "-----------------------------------"

INDEX2_OUTPUT=$(kimi-tachi memory index 2>&1)
if echo "$INDEX2_OUTPUT" | grep -q "skipped"; then
    SKIPPED=$(echo "$INDEX2_OUTPUT" | grep -o '[0-9]\+ skipped' | head -1)
    pass "Incremental indexing works ($SKIPPED)"
else
    warn "Incremental indexing may not be working"
fi

echo ""
echo "Step 7: Testing memory status..."
echo "-----------------------------------"

if kimi-tachi memory status > /dev/null 2>&1; then
    pass "Memory status check works"
else
    fail "Memory status check failed"
fi

echo ""
echo "Step 8: Testing global memory..."
echo "-----------------------------------"

if kimi-tachi memory register-global --project test-memory > /dev/null 2>&1; then
    pass "Global memory registration works"
    
    if kimi-tachi memory sync-global --project test-memory > /dev/null 2>&1; then
        pass "Global memory sync works"
    else
        warn "Global memory sync may have issues"
    fi
else
    warn "Global memory registration may have issues"
fi

echo ""
echo "Step 9: Testing Agent recall..."
echo "-----------------------------------"

RECALL_OUTPUT=$(kimi-tachi memory recall --agent kamaji 2>&1)
if echo "$RECALL_OUTPUT" | grep -q "kamaji's Memory Profile"; then
    pass "Agent recall works"
else
    fail "Agent recall failed"
    echo "$RECALL_OUTPUT"
fi

echo ""
echo "======================================"
echo "Test Summary"
echo "======================================"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo ""

# Cleanup
cd /
rm -rf "$TEST_DIR"
echo "Cleaned up test directory"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed! ✓${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please check the output above.${NC}"
    exit 1
fi
