# v0.1.0

## What changed

- Added a new local-first CLI for scoring instruction-context files in AGENTS.md, CLAUDE.md, .cursorrules, .cursor/rules/*.md, and .github/copilot-instructions.md.
- Added category-based detection for:
  - clarity
  - verification instructions
  - stale references/placeholders
  - contradictions
  - destructive permission language
  - prompt-injection-prone phrasing
  - repetition/excessive length
- Added Markdown and JSON output formats, file output option, and `--fail-under` CI gate.
- Added unit tests for discovery, scoring, issue detection, output formats, and gate behavior.
- Added release/readme/metadata/community files for repository completeness.
