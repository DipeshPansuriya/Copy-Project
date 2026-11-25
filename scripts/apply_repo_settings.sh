#!/usr/bin/env bash
# apply_repo_settings.sh — Apply branch protection + security settings to GitHub.
#
# Mirrors the hardening applied to DipeshPansuriya/MLX_Model_App:
#   - main branch protection (PR required, 1 review, status checks, signed commits,
#     linear history, no force-push, no deletion, admins included)
#   - secret scanning + push protection
#   - Dependabot alerts + security updates
#   - vulnerability alerts
#
# Requirements: curl, jq, and a token with `repo` + `admin:repo_hook` scope.
#
# Usage:
#   export GITHUB_TOKEN=ghp_xxx
#   ./scripts/apply_repo_settings.sh                 # apply
#   ./scripts/apply_repo_settings.sh --dry-run       # print requests only
#   ./scripts/apply_repo_settings.sh --verify        # read back current state

set -euo pipefail

OWNER="${GITHUB_OWNER:-DipeshPansuriya}"
REPO="${GITHUB_REPO:-Copy-Project}"
BRANCH="${GITHUB_BRANCH:-main}"
API="https://api.github.com"
MODE="${1:---apply}"

if [ "$MODE" != "--dry-run" ] && [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "❌ GITHUB_TOKEN is not set. Export a token with 'repo' scope." >&2
  exit 1
fi

command -v jq >/dev/null 2>&1 || { echo "❌ jq is required" >&2; exit 1; }

auth_header=()
if [ -n "${GITHUB_TOKEN:-}" ]; then
  auth_header=(-H "Authorization: Bearer ${GITHUB_TOKEN}")
fi

api() {
  local method="$1" path="$2" body="${3:-}"
  if [ "$MODE" = "--dry-run" ]; then
    # Print to stderr so callers redirecting stdout still surface the request.
    {
      echo "DRY-RUN ${method} ${API}${path}"
      [ -n "$body" ] && echo "$body" | jq .
    } >&2
    return 0
  fi
  if [ -n "$body" ]; then
    curl -sS -X "$method" "${API}${path}" \
      "${auth_header[@]}" \
      -H "Accept: application/vnd.github+json" \
      -H "X-GitHub-Api-Version: 2022-11-28" \
      -d "$body"
  else
    curl -sS -X "$method" "${API}${path}" \
      "${auth_header[@]}" \
      -H "Accept: application/vnd.github+json" \
      -H "X-GitHub-Api-Version: 2022-11-28"
  fi
}

echo "========================================="
echo "  GitHub repo hardening: ${OWNER}/${REPO}"
echo "  Mode: ${MODE}"
echo "========================================="

if [ "$MODE" = "--verify" ]; then
  echo ""
  echo "--- repository visibility & features ---"
  api GET "/repos/${OWNER}/${REPO}" | jq '{
    visibility,
    private,
    has_issues,
    has_wiki,
    allow_squash_merge,
    allow_merge_commit,
    allow_rebase_merge,
    delete_branch_on_merge,
    security_and_analysis
  }'

  echo ""
  echo "--- branch protection (${BRANCH}) ---"
  api GET "/repos/${OWNER}/${REPO}/branches/${BRANCH}/protection" | jq '.'
  exit 0
fi

# --- 1. Repository features ------------------------------------------------
api PATCH "/repos/${OWNER}/${REPO}" "$(jq -n '{
  has_issues: true,
  has_wiki: false,
  has_projects: false,
  allow_squash_merge: true,
  allow_merge_commit: false,
  allow_rebase_merge: false,
  delete_branch_on_merge: true,
  allow_auto_merge: false,
  allow_update_branch: true
}')" >/dev/null
echo "✓ repository merge/feature settings applied"

# --- 2. Vulnerability alerts ----------------------------------------------
api PUT "/repos/${OWNER}/${REPO}/vulnerability-alerts" >/dev/null 2>&1 \
  && echo "✓ vulnerability alerts enabled" \
  || echo "⚠ could not enable vulnerability alerts (may already be on)"

# --- 3. Automated security fixes ------------------------------------------
api PUT "/repos/${OWNER}/${REPO}/automated-security-fixes" >/dev/null 2>&1 \
  && echo "✓ Dependabot security updates enabled" \
  || echo "⚠ could not enable automated security fixes"

# --- 4. Secret scanning + push protection ---------------------------------
api PATCH "/repos/${OWNER}/${REPO}" "$(jq -n '{
  security_and_analysis: {
    secret_scanning: { status: "enabled" },
    secret_scanning_push_protection: { status: "enabled" },
    secret_scanning_non_provider_patterns: { status: "enabled" },
    secret_scanning_validity_checks: { status: "enabled" }
  }
}')" >/dev/null 2>&1 \
  && echo "✓ secret scanning + push protection enabled" \
  || echo "⚠ secret scanning requires a public repo or GitHub Advanced Security"

# --- 5. Branch protection on main -----------------------------------------
api PUT "/repos/${OWNER}/${REPO}/branches/${BRANCH}/protection" "$(jq -n '{
  required_status_checks: {
    strict: true,
    contexts: [
      "Secret Scanning",
      "Dependency Review",
      "Analyze (python)",
      "Lint & Format",
      "Run Tests",
      "Docker Build",
      "PR Review Checks"
    ]
  },
  enforce_admins: true,
  required_pull_request_reviews: {
    dismiss_stale_reviews: true,
    require_code_owner_reviews: true,
    required_approving_review_count: 1,
    require_last_push_approval: true
  },
  restrictions: null,
  required_linear_history: true,
  allow_force_pushes: false,
  allow_deletions: false,
  block_creations: false,
  required_conversation_resolution: true,
  lock_branch: false,
  allow_fork_syncing: true
}')" >/dev/null
echo "✓ branch protection applied to ${BRANCH}"

# --- 6. Require signed commits --------------------------------------------
api POST "/repos/${OWNER}/${REPO}/branches/${BRANCH}/protection/required_signatures" >/dev/null 2>&1 \
  && echo "✓ signed commits required" \
  || echo "⚠ could not require signed commits (needs a signing key configured)"

echo ""
echo "Done. Verify with: ./scripts/apply_repo_settings.sh --verify"
