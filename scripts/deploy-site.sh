#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

CNAME="${1:-lorekeeper.borck.education}"
REPO="${SITE_REPO:-https://github.com/michael-borck/lorekeeper-site.git}"
BUILD="_site.build"

KEY="${LOREKEEPER_KEY:-$HOME/.lorekeeper/lorekeeper-signing.pem}"
if [ ! -f "$KEY" ]; then
  echo "Missing signing key: $KEY" >&2
  echo "Run 'python3 -m lorekeeper keygen --trusted player/trusted-keys.js' first." >&2
  exit 1
fi

rm -rf "$BUILD"
python3 -m lorekeeper store --out store --key "$KEY"
python3 -m lorekeeper site --out "$BUILD" --cname "$CNAME"

mkdir -p _site
rsync -a --delete --exclude '.git' "$BUILD/" _site/
rm -rf "$BUILD"

cd _site
if [ ! -d .git ]; then
  git init -b main
fi
git remote get-url origin >/dev/null 2>&1 || git remote add origin "$REPO"

git add -A
git commit -m "Deploy Lorekeeper $(date -u +%Y-%m-%dT%H:%M:%SZ)" || true
git push origin main
