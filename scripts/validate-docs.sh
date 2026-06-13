#!/usr/bin/env bash
set -euo pipefail

required_paths=(
  "AGENTS.md"
  "CLAUDE.md"
  "README.md"
  "docs/README.md"
  "docs/product/README.md"
  "docs/product/prd.md"
  "docs/design/README.md"
  "docs/design/ui-guidelines.md"
  "docs/tech/README.md"
  "docs/tech/architecture.md"
  "docs/test/README.md"
  "docs/test/test-plan.md"
  "docs/verification/README.md"
  "docs/verification/scenarios.md"
  "docs/agent/README.md"
  "docs/agent/context.md"
  "docs/templates/README.md"
)

for path in "${required_paths[@]}"; do
  if [[ ! -e "$path" ]]; then
    echo "missing required path: $path" >&2
    exit 1
  fi
done

markdown_files=()
if command -v rg >/dev/null 2>&1; then
  while IFS= read -r file; do
    markdown_files+=("$file")
  done < <(rg --files -g '*.md' .)
else
  while IFS= read -r file; do
    markdown_files+=("$file")
  done < <(find . -name '*.md' -type f)
fi

for file in "${markdown_files[@]}"; do
  dir=$(dirname "$file")
  while IFS= read -r link; do
    target=${link%%#*}
    [[ "$target" =~ ^https?:// ]] && continue
    [[ "$target" =~ ^mailto: ]] && continue
    if [[ "$target" = /* ]]; then
      candidate=".$target"
    else
      candidate="$dir/$target"
    fi
    if [[ ! -e "$candidate" ]]; then
      echo "broken markdown link in $file: $link" >&2
      exit 1
    fi
  done < <(perl -ne 'while (/\[[^]]+\]\(([^)#][^):]*\.md(?:#[^)]+)?)\)/g) { print "$1\n" }' "$file")
done

echo "docs validation passed (${#markdown_files[@]} markdown files)"
