#!/usr/bin/env bash
set -euo pipefail

# One-time migration: copy docs from the Jekyll branch into the MkDocs tree.
# - Source branch: docs-jekyll-site
# - Source root:   docs/
# - Dest branch:   mkdocs (current)
# - Dest root:     docs/

SRC_BRANCH=${1:-docs-jekyll-site}
SRC_DIR=docs
DST_DIR=docs

if ! git rev-parse --verify "$SRC_BRANCH" >/dev/null 2>&1; then
  echo "fatal: branch $SRC_BRANCH not found" >&2
  exit 1
fi

tmpdir=$(mktemp -d)
cleanup(){ rm -rf "$tmpdir"; }
trap cleanup EXIT

echo "• Exporting $SRC_BRANCH:$SRC_DIR to temp..."
git archive "$SRC_BRANCH" "$SRC_DIR" | tar -x -C "$tmpdir"

echo "• Copying Markdown and common assets into $DST_DIR/ ..."
mkdir -p "$DST_DIR"
rsync -a --delete --exclude '.DS_Store' --exclude '.pytest_cache' --exclude '.venv' \
  "$tmpdir/$SRC_DIR/" "$DST_DIR/"

echo "• Done. Review diffs, then commit and push on mkdocs."
