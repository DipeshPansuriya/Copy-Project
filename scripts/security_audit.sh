#!/usr/bin/env bash
# security_audit.sh — 21-point security audit for OpenClipboard
# Replicated from MLX_Model_App's security audit script.
#
# Usage:
#   ./scripts/security_audit.sh --quick   # fast pre-commit check
#   ./scripts/security_audit.sh --full    # full audit before push/release

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:---full}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS=0
FAIL=0
WARN=0

pass_check() { echo -e "${GREEN}✓ PASS${NC}: $1"; PASS=$((PASS + 1)); }
fail_check() { echo -e "${RED}✗ FAIL${NC}: $1"; FAIL=$((FAIL + 1)); }
warn_check() { echo -e "${YELLOW}⚠ WARN${NC}: $1"; WARN=$((WARN + 1)); }

echo "========================================="
echo "  OpenClipboard Security Audit ($MODE)"
echo "========================================="
echo ""

# --- 1. .env not committed ---------------------------------------------------
if git -C "$ROOT" ls-files --error-unmatch ".env" >/dev/null 2>&1; then
  fail_check ".env is tracked in git"
else
  pass_check ".env is not tracked in git"
fi

# --- 2. .env.example exists --------------------------------------------------
if [ -f "$ROOT/.env.example" ]; then
  pass_check ".env.example exists"
else
  fail_check ".env.example missing"
fi

# --- 3. SECURITY.md exists ---------------------------------------------------
if [ -f "$ROOT/SECURITY.md" ]; then
  pass_check "SECURITY.md exists"
else
  fail_check "SECURITY.md missing"
fi

# --- 4. .gitignore exists and covers .env -----------------------------------
if [ -f "$ROOT/.gitignore" ]; then
  if grep -qE '^\.env($|\.|/)' "$ROOT/.gitignore"; then
    pass_check ".gitignore excludes .env files"
  else
    fail_check ".gitignore does not exclude .env"
  fi
else
  fail_check ".gitignore missing"
fi

# --- 5. Branch protection docs exist -----------------------------------------
if [ -f "$ROOT/docs/BRANCH-POLICY.md" ]; then
  pass_check "Branch policy document exists"
else
  warn_check "Branch policy document missing"
fi

# --- 6. Push policy docs exist -----------------------------------------------
if [ -f "$ROOT/docs/PUSH-POLICY.md" ]; then
  pass_check "Push policy document exists"
else
  warn_check "Push policy document missing"
fi

# --- 7. Code owners file -----------------------------------------------------
if [ -f "$ROOT/.github/CODEOWNERS" ]; then
  pass_check "CODEOWNERS exists"
else
  warn_check "CODEOWNERS missing"
fi

# --- 8. Dependabot config ----------------------------------------------------
if [ -f "$ROOT/.github/dependabot.yml" ]; then
  pass_check "Dependabot config exists"
else
  warn_check "Dependabot config missing"
fi

# --- 9. Secret scanner script ------------------------------------------------
if [ -x "$ROOT/scripts/check_secrets.py" ]; then
  pass_check "Secret scanner script exists"
else
  fail_check "Secret scanner script missing"
fi

# --- 10. Secret scanner actually runs (quick) -------------------------------
if [ "$MODE" = "--full" ] || [ "$MODE" = "--quick" ]; then
  if python3 "$ROOT/scripts/check_secrets.py" --quick >/dev/null 2>&1; then
    pass_check "Secret scanner passes"
  else
    warn_check "Secret scanner found potential secrets (review required)"
  fi
fi

# --- 11. No hardcoded admin passwords in source ------------------------------
if grep -rniE '(admin_password|admin_passwd|admin_pwd)\s*[:=]\s*["'"'"'][^"'"'"']+["'"'"']' "$ROOT/backend/app/" 2>/dev/null | grep -vE '\.pyc|#|test|example|os\.getenv' | grep -q .; then
  warn_check "Possible hardcoded admin credentials in backend source"
else
  pass_check "No hardcoded admin credentials in backend source"
fi

# --- 12. Security headers present in main.py ---------------------------------
if grep -q 'X-Content-Type-Options' "$ROOT/backend/app/main.py" 2>/dev/null; then
  pass_check "X-Content-Type-Options header set"
else
  fail_check "X-Content-Type-Options header missing"
fi

if grep -q 'X-Frame-Options' "$ROOT/backend/app/main.py" 2>/dev/null; then
  pass_check "X-Frame-Options header set"
else
  fail_check "X-Frame-Options header missing"
fi

if grep -q 'Strict-Transport-Security' "$ROOT/backend/app/main.py" 2>/dev/null; then
  pass_check "HSTS header set"
else
  fail_check "HSTS header missing"
fi

# --- 13. TrustedHostMiddleware present ---------------------------------------
if grep -q 'TrustedHostMiddleware' "$ROOT/backend/app/main.py" 2>/dev/null; then
  pass_check "TrustedHostMiddleware configured"
else
  fail_check "TrustedHostMiddleware missing"
fi

# --- 14. Rate limiting configured --------------------------------------------
if grep -q 'slowapi\|limiter\|rate_limit' "$ROOT/backend/app/config.py" 2>/dev/null; then
  pass_check "Rate limiting configured"
else
  warn_check "Rate limiting not found in config"
fi

# --- 15. Dockerfile non-root user --------------------------------------------
if grep -qE 'USER|useradd|nobody|nonroot' "$ROOT/backend/Dockerfile" 2>/dev/null; then
  pass_check "Dockerfile specifies non-root user"
else
  warn_check "Dockerfile does not specify non-root user"
fi

# --- 16. Pre-commit hooks exist ----------------------------------------------
if [ -f "$ROOT/.githooks/pre-commit" ]; then
  pass_check "Pre-commit hook exists"
else
  fail_check "Pre-commit hook missing"
fi

if [ -f "$ROOT/.githooks/pre-push" ]; then
  pass_check "Pre-push hook exists"
else
  fail_check "Pre-push hook missing"
fi

# --- 17. Security workflows exist --------------------------------------------
if [ -f "$ROOT/.github/workflows/security.yml" ]; then
  pass_check "Security scanning workflow exists"
else
  fail_check "Security scanning workflow missing"
fi

# --- 18. GitHub Actions quality workflow -------------------------------------
if [ -f "$ROOT/.github/workflows/quality.yml" ]; then
  pass_check "Quality workflow exists"
else
  warn_check "Quality workflow missing"
fi

# --- 19. Test files exist ----------------------------------------------------
if [ -d "$ROOT/backend/tests" ] && [ "$(ls -A "$ROOT/backend/tests" 2>/dev/null)" ]; then
  pass_check "Test suite exists"
else
  warn_check "No automated test suite found"
fi

# --- 20. No secrets in docker-compose files ----------------------------------
if grep -riE 'password|secret' "$ROOT/docker-compose*.yml" "$ROOT/backend/Dockerfile" 2>/dev/null | grep -viE 'example|\$\{.*\}|CHANGEME|yourdomain|MINIO_ROOT|PG_PASSWORD|admin_password' | grep -q .; then
  warn_check "Possible hardcoded secrets in compose/Dockerfile"
else
  pass_check "No hardcoded secrets in compose/Dockerfile"
fi

# --- 21. Executable file detection in items.py ------------------------------
if grep -q 'EXECUTABLE_MAGIC\|\\x7fELF\|MZ\|Mach-O\|#!' "$ROOT/backend/app/api/items.py" 2>/dev/null; then
  pass_check "Executable file magic detection present"
else
  fail_check "Executable file magic detection missing"
fi

echo ""
echo "========================================="
echo "  Results: ${PASS} passed, ${FAIL} failed, ${WARN} warnings"
echo "========================================="

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi

exit 0
