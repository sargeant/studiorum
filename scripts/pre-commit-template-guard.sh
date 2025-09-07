#!/usr/bin/env bash
# Fail pre-commit if legacy TemplateService render calls appear in templates.

set -euo pipefail

PATTERN='template_service\.render_entry_(description|content_only)\s*\('

# No allowlist: all templates must use smart_render_entry with processor/context.


files=("$@")
if [[ ${#files[@]} -eq 0 ]]; then
  while IFS= read -r -d '' f; do files+=("$f"); done < <(
    find src/studiorum/latex_engine/templates -type f -name '*.tex.j2' -print0
  )
fi

violations=()

for f in "${files[@]}"; do
  [[ -f "$f" ]] || continue
  # No allowlist: scan all template files
  # Strip Jinja2 comment blocks (<#-- ... --#>) before scanning
  filtered=$(awk '
    BEGIN{incomment=0}
    {
      start=index($0,"<#--"); end=index($0,"--#>")
      if (start && !end) incomment=1
      if (!incomment && start && end && start<end) { line=$0; gsub(/<#--.*--#>/, "", line); print line; next }
      if (!incomment) print
      if (end && !start) incomment=0
    }
  ' "$f")

  if grep -E "$PATTERN" >/dev/null <<< "$filtered"; then
    violations+=("$f")
  fi
done

if [[ ${#violations[@]} -gt 0 ]]; then
  echo "Template legacy render calls detected:" >&2
  for f in "${violations[@]}"; do
    echo "  - $f" >&2
    # Show offending lines with numbers
    awk '
      BEGIN{incomment=0}
      {
        start=index($0,"<#--"); end=index($0,"--#>")
        if (start && !end) incomment=1
        if (!incomment && start && end && start<end) { line=$0; gsub(/<#--.*--#>/, "", line); print NR ":" line; next }
        if (!incomment) print NR ":" $0
        if (end && !start) incomment=0
      }
    ' "$f" | grep -nE "$PATTERN" || true
  done
  cat >&2 <<'MSG'
Please replace template_service.render_entry_description/content_only with:
  - smart_render_entry(entry, entry_processor, rendering_context)
Import with context:
  <@ from "_entry_macros.tex.j2" import smart_render_entry with context @>
MSG
  exit 1
fi

exit 0
