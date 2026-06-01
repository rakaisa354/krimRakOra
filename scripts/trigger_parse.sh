#!/bin/bash
# Trigger GitHub Actions parse-statement workflow via API
# Usage: ./scripts/trigger_parse.sh ICICI_Bank.md
#
# Requires: GITHUB_TOKEN env var with repo:workflow scope
# Get one at: https://github.com/settings/tokens

FILE=${1:?"Usage: trigger_parse.sh <filename>"}
REPO="rakaisa354/krimRakOra"

curl -s -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/$REPO/dispatches" \
  -d "{\"event_type\": \"parse-statement\", \"client_payload\": {\"filename\": \"$FILE\"}}"

echo "Triggered parse for: $FILE"
echo "Watch: https://github.com/$REPO/actions"
