#!/bin/bash
set -e
cd "/Users/rakeshkrishnan/Documents/02_Personal/Claude Projects/krimRakOra"

git add CLAUDE.md
git add docs/WIKI.md

echo ""
echo "===== git status ====="
git status

echo ""
echo "===== committing ====="
git commit -m "docs: update CLAUDE.md progress + add project wiki (2026-08-01 session)"

echo ""
echo "===== pushing ====="
git push

echo ""
echo "===== done — log ====="
git log -3
