#!/bin/bash
# resolve-template.sh — Resolve Spec Kit templates
# Usage: resolve-template.sh <template-name> [--json]

set -euo pipefail

TEMPLATE_NAME="${1:-constitution-template}"
OUTPUT_FORMAT="${2:---text}"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
TEMPLATE_DIR="${PROJECT_ROOT}/.specify/templates"

if [[ "$OUTPUT_FORMAT" == "--json" ]]; then
  # Output as JSON with TEMPLATE_CONTENT key
  if [[ -f "${TEMPLATE_DIR}/${TEMPLATE_NAME}.md" ]]; then
    CONTENT=$(cat "${TEMPLATE_DIR}/${TEMPLATE_NAME}.md")
    # Escape newlines and quotes for JSON
    ESCAPED=$(printf '%s\n' "$CONTENT" | jq -Rs '.')
    echo "{\"TEMPLATE_CONTENT\": $ESCAPED, \"TEMPLATE_PATH\": \"${TEMPLATE_DIR}/${TEMPLATE_NAME}.md\"}"
  else
    echo "{\"ERROR\": \"Template not found: ${TEMPLATE_DIR}/${TEMPLATE_NAME}.md\"}" >&2
    exit 1
  fi
else
  # Output as plain text
  if [[ -f "${TEMPLATE_DIR}/${TEMPLATE_NAME}.md" ]]; then
    cat "${TEMPLATE_DIR}/${TEMPLATE_NAME}.md"
  else
    echo "Template not found: ${TEMPLATE_DIR}/${TEMPLATE_NAME}.md" >&2
    exit 1
  fi
fi
