#!/bin/bash
# Commit CLAUDE.md + docs/WIKI.md together at the end of a session.
# Usage: ./krimrakora-docs-commit.sh "commit message describing this session's changes"
set -e
cd "/Users/rakeshkrishnan/Documents/02_Personal/Claude Projects/krimRakOra"

MSG="${1:?Usage: ./krimrakora-docs-commit.sh \"commit message\"}"

git add CLAUDE.md
git add docs/WIKI.md

echo ""
echo "===== git status ====="
git status

echo ""
echo "===== committing ====="
git commit -m "$MSG"

echo ""
echo "===== pushing ====="
git push

echo ""
echo "===== done — log ====="
git log -3
