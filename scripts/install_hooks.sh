#!/usr/bin/env bash
# install_hooks.sh — Install Git hooks for OpenClipboard
#
# Usage: ./scripts/install_hooks.sh
#   Sets core.hooksPath to .githooks and makes hooks executable.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "🔧 Installing Git hooks..."

# Make hooks executable
chmod +x "$ROOT/.githooks/pre-commit"
chmod +x "$ROOT/.githooks/pre-push"
chmod +x "$ROOT/scripts/check_secrets.py"
chmod +x "$ROOT/scripts/security_audit.sh"

# Configure git to use .githooks as the hooks path
git -C "$ROOT" config core.hooksPath "$ROOT/.githooks"

echo "✅ Git hooks installed at $ROOT/.githooks"
echo "   core.hooksPath is now set to .githooks"
echo ""
echo "   Pre-commit hook will run on every commit."
echo "   Pre-push hook will run on every push."
echo "   Direct pushes to main are blocked (use PRs)."
