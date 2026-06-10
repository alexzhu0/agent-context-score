# Agent Context Score

Score instruction-context files in a directory and catch risky language before an agent consumes them.

## Why

`agent-context-score` scans common instruction surfaces and produces a deterministic score for:

- Clarity of the instructions
- Presence of verification guidance
- Stale references or placeholders
- Contradictions inside guidance
- Destructive permission language
- Prompt-injection-prone phrasing
- Excessive repetition or unusually long instruction blocks

## Quickstart

```bash
PYTHONPATH=src python3 -m agent_context_score examples/bad --format markdown
```

## Install

```bash
git clone <repo>
cd repos/agent-context-score
PYTHONPATH=src python3 -m agent_context_score --help
```

## Examples

```bash
PYTHONPATH=src python3 -m agent_context_score examples/bad --format markdown
PYTHONPATH=src python3 -m agent_context_score examples/good --format json
PYTHONPATH=src python3 -m agent_context_score /path/to/project --format markdown --output /tmp/context-score.md
PYTHONPATH=src python3 -m agent_context_score /path/to/project --fail-under 80
```

## API

The stable interface is the CLI:

```bash
PYTHONPATH=src python3 -m agent_context_score TARGET_DIR --format markdown
PYTHONPATH=src python3 -m agent_context_score TARGET_DIR --format json --output context-score.json
PYTHONPATH=src python3 -m agent_context_score TARGET_DIR --fail-under 80
```

Options:

- `target` scans a directory for known agent instruction files.
- `--format markdown|json` selects human or machine output.
- `--output PATH` writes output to a file.
- `--fail-under SCORE` exits with code `2` when the score is below threshold.

## Contributing

```bash
python3 -m unittest discover -s tests
```

Open issues with the smallest instruction file that reproduces the score or finding. Keep rules deterministic and add tests for every new detection.

## FAQ

- Does this call an LLM? No. It is a deterministic local scanner.
- Does this rewrite my instruction files? No. It reports score and findings only.
- Which files are scanned? The initial set is listed below and can be expanded by contribution.

## Scanned Files

The CLI currently scans:

- `AGENTS.md`
- `CLAUDE.md`
- `.cursorrules`
- `.github/copilot-instructions.md`
- `.cursor/rules/*.md`

## Notes

- No external network calls are used.
- Output is stable for the same file set and heuristics.

## License

MIT
