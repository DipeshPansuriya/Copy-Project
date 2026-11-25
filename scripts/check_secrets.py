#!/usr/bin/env python3
"""check_secrets.py — Scan repository for secrets before commits/pushes.

Implements 19 security rules replicated from MLX_Model_App's pre-commit hooks.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# --- Secret patterns (19 rules) ---------------------------------------------
# These match actual secret VALUES, not variable names or env var references.
SECRET_RULES = [
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
    (r"(?i)aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{40}", "AWS Secret Access Key"),
    (r"(?i)github[_-]?token\s*[:=]\s*['\"]?ghp_[A-Za-z0-9]{36}", "GitHub Personal Access Token"),
    (r"(?i)gitlab[_-]?token\s*[:=]\s*['\"]?glpt-[A-Za-z0-9-_]{20,}", "GitLab Token"),
    (r"(?i)slack[_-]?token\s*[:=]\s*['\"]?xox[baprs]-[A-Za-z0-9-]+", "Slack Token"),
    (r"(?i)stripe[_-]?(live|test)[_-]?key\s*[:=]\s*['\"]?sk_[A-Za-z0-9]{24,}", "Stripe Secret Key"),
    (r"(?i)stripe[_-]?(live|test)[_-]?publishable[_-]?key\s*[:=]\s*['\"]?pk_[A-Za-z0-9]{24,}", "Stripe Publishable Key"),
    (r"(?i)sendgrid[_-]?api[_-]?key\s*[:=]\s*['\"]?SG\.[A-Za-z0-9_-]{22,}", "SendGrid API Key"),
    (r"(?i)mailgun[_-]?api[_-]?key\s*[:=]\s*['\"]?key-[A-Za-z0-9]{32}", "Mailgun API Key"),
    (r"(?i)twilio[_-]?account[_-]?sid\s*[:=]\s*['\"]?AC[a-z0-9]{32}", "Twilio Account SID"),
    (r"(?i)twilio[_-]?auth[_-]?token\s*[:=]\s*['\"]?[a-f0-9]{32}", "Twilio Auth Token"),
    (r"(?i)mongodb[_-]?(uri|connection[_-]?string)\s*[:=]\s*['\"]?mongodb\+srv://[^'\"]+", "MongoDB Connection String"),
    (r"(?i)(postgres|postgresql|pg)://[^:\s]+:[^:\s]+@[^/\s]+", "Database Connection String with credentials"),
    (r"(?i)redis://[^:@\s]+:[^:@\s]+@[^/\s]+", "Redis connection string with credentials"),
    (r"(?i)private[_-]?key\s*[:=]\s*['\"]?-----BEGIN[^-]+-----", "Private Key"),
    (r"(?i)ssh-rsa\s+[A-Za-z0-9+/]+[=]{0,3}", "SSH Public Key"),
    (r"(?i)(CLIP_ADMIN_PASSWORD|MINIO_SECRET_KEY|PG_PASSWORD)\s*=\s*['\"][^'\"]{8,}['\"]", "Hardcoded application secret value"),
    (r"(?i)Bearer\s+[A-Za-z0-9\-\._~+/]{20,}=", "Bearer token"),
]

COMPILED_RULES = [(re.compile(pattern), name) for pattern, name in SECRET_RULES]

# Files/paths to skip
SKIP_PATHS = {
    ".git/",
    "__pycache__/",
    ".pyc",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg",
    ".woff", ".woff2", ".ttf", ".eot",
    ".zip", ".tar", ".gz", ".bz2", ".7z",
    ".lock",
    "node_modules/",
    ".venv/",
    "venv/",
    ".env.example",  # template file is allowed
    "check_secrets.py",  # this file contains the patterns
    "security_audit.sh",
}

# Files that are documentation/examples — allowed to mention secret patterns
ALLOWLIST_NAMES = {
    ".env.example",
    "README.md",
    "SECURITY.md",
    "HOSTINGER_DEPLOY.md",
    "SECURITY-AUDIT.md",
    "check_secrets.py",
    "security_audit.sh",
}

ALLOWLIST_PATHS = {
    "docs/conventions/configuration-and-secrets.md",
    "docs/conventions/secret-protector.md",
    "docs/SECURITY-AUDIT.md",
}

EXCLUDED_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules"}


def should_skip(path: Path) -> bool:
    parts = path.parts
    for part in parts:
        if part in EXCLUDED_DIRS:
            return True
    for suffix in SKIP_PATHS:
        if str(path).endswith(suffix):
            return True
    if path.name in ALLOWLIST_NAMES:
        return True
    rel = str(path.relative_to(ROOT))
    if rel in ALLOWLIST_PATHS:
        return True
    return False


def is_config_declaration(line: str) -> bool:
    """Return True if the line is a type-annotated config variable declaration."""
    stripped = line.strip()
    # Skip type-annotated assignments like: minio_secret_key: str = os.getenv(...)
    if re.search(r':\s*\w+\s*=\s*os\.getenv', stripped):
        return True
    # Skip f-string DSN templates like: return f"postgresql://{...}:{...}@..."
    if 'f"' in stripped or "f'" in stripped:
        if '{' in stripped and '}' in stripped:
            return True
    # Skip env var references like ${MINIO_SECRET_KEY}
    if '${' in stripped and '}' in stripped:
        return True
    return False


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    """Scan a single file for secrets. Returns list of (line_number, matched_text, rule_name)."""
    findings: list[tuple[int, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings

    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        # Skip comments and documentation lines
        if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("*"):
            continue
        # Skip config type declarations and env var templates
        if is_config_declaration(stripped):
            continue
        for regex, name in COMPILED_RULES:
            match = regex.search(line)
            if match:
                findings.append((line_no, match.group(0)[:80], name))

    return findings


def scan_repo(quick: bool = False) -> list[tuple[Path, int, str, str]]:
    """Scan the whole repository. Returns list of (file, line_no, match, rule_name)."""
    findings: list[tuple[Path, int, str, str]] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if should_skip(path):
            continue
        if quick and path.suffix not in {".py", ".env", ".yml", ".yaml", ".sh", ".md", ".toml", ".cfg", ".ini", ".json"}:
            continue
        try:
            file_findings = scan_file(path)
        except Exception:
            continue
        for line_no, match, rule_name in file_findings:
            findings.append((path, line_no, match, rule_name))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan repository for hardcoded secrets")
    parser.add_argument("--push", action="store_true", help="Run in push mode (full scan)")
    parser.add_argument("--quick", action="store_true", help="Quick scan of common file types")
    args = parser.parse_args()

    quick = args.quick or not args.push
    findings = scan_repo(quick=quick)

    if findings:
        print("❌ SECRETS DETECTED — potential hardcoded secrets found:")
        for path, line_no, _match, rule_name in findings:
            rel = path.relative_to(ROOT)
            # Never echo the matched value: this output lands in CI logs.
            print(f"  {rel}:{line_no} — {rule_name} (value redacted)")
        print(f"\nTotal findings: {len(findings)}")
        print("Move secrets to environment variables or .env (never commit .env).")
        return 1

    print("✅ No secrets detected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
