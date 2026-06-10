"""CLI for scoring AI-context instruction files."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence

MAX_SCORE = 100.0


ISSUE_WEIGHTS = {
    "clarity": 6,
    "verification_instructions": 8,
    "stale_references": 6,
    "contradictions": 10,
    "destructive_permission_language": 16,
    "prompt_injection": 18,
    "repetition": 7,
    "coverage": 8,
}


VERIFICATION_HINTS = (
    "verify",
    "validation",
    "test",
    "lint",
    "ci",
    "check",
    "run",
    "assert",
)

STALE_PATTERNS = (
    r"\btodo\b",
    r"\btbd\b",
    r"\bfixme\b",
    r"\bdeprecated\b",
    r"\blegacy\b",
    r"\boutdated\b",
    r"\bmaster\b",
)

CONTRADICTION_PATTERNS = (
    (r"\bmust\b", r"\bmust not\b"),
    (r"\balways\b", r"\bnever\b"),
    (r"\ballow\b", r"\bforbid\b"),
    (r"\bincrease\b", r"\bdecrease\b"),
    (r"\benable\b", r"\bdisable\b"),
)

DESTRUCTIVE_PATTERNS = (
    r"\brm\s+-rf\b",
    r"\bsudo\s+rm\b",
    r"\bsudo\s+sh\b",
    r"\bdrop\s+database\b",
    r"\bdelete\s+all\b",
    r"\bremove\s+all\b",
    r"\bformat\s+disk\b",
    r"\btruncate\s+\w+\s+table\b",
    r"\bwipe\s+(all|everything)\b",
    r"\bforcibly\s+close\b",
)

INJECTION_PATTERNS = (
    r"\bignore\s+(all|previous|current)\s+instructions\b",
    r"\bdisregard\s+(all|previous|current)\s+instructions\b",
    r"\bbypass\s+policy\b",
    r"\bignore.*and\s+follow\s+this\b",
    r"\byou\s+are\s+now\b.*\bno\s+restrictions\b",
    r"\bdo\s+anything\s+you\s+can\b",
    r"\bthis\s+instruction\s+overrides\s+everything\b",
)


@dataclass(frozen=True)
class Issue:
    path: str
    category: str
    message: str
    weight: int

    def to_dict(self) -> Dict[str, Any]:
        return {"path": self.path, "category": self.category, "message": self.message, "weight": self.weight}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Score AI context instruction files under a target directory.")
    parser.add_argument("target", help="Target directory to scan for instruction files.")
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format: markdown or json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write formatted output to this file.",
    )
    parser.add_argument(
        "--fail-under",
        type=float,
        default=None,
        metavar="SCORE",
        dest="fail_under",
        help="Exit with code 2 when score is below this value.",
    )
    return parser


def discover_instruction_files(target_dir: Path) -> List[Path]:
    files: List[Path] = []
    for path in target_dir.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(target_dir).as_posix()
        if path.name == "AGENTS.md":
            files.append(path)
            continue
        if path.name == "CLAUDE.md":
            files.append(path)
            continue
        if path.name == ".cursorrules":
            files.append(path)
            continue
        if path.name == "copilot-instructions.md" and ".github" in path.parts:
            files.append(path)
            continue
        if path.suffix.lower() == ".md" and "/.cursor/rules/" in f"/{rel}/":
            files.append(path)
            continue
    return sorted(files)


def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _has_heading(text: str) -> bool:
    return any(line.startswith("#") for line in text.splitlines())


def _has_verification_guidance(text: str) -> bool:
    lower = text.lower()
    return any(token in lower for token in VERIFICATION_HINTS)


def _match_any(patterns: Sequence[str], text: str) -> List[str]:
    hits = []
    for pattern in patterns:
        found = [m.group(0) for m in re.finditer(pattern, text, flags=re.IGNORECASE)]
        if found:
            hits.extend(found)
    return hits


def _match_contradictions(text: str) -> List[str]:
    lower = text.lower()
    hits: List[str] = []
    for left, right in CONTRADICTION_PATTERNS:
        if re.search(left, lower) and re.search(right, lower):
            hits.append(f"conflicting phrases: {left} and {right}")
    return hits


def _has_repetition(text: str) -> bool:
    lines = [re.sub(r"\s+", " ", line.strip().lower()) for line in text.splitlines() if line.strip()]
    if len(lines) < 6:
        return False
    unique_ratio = len(set(lines)) / len(lines)
    counter = Counter(lines)
    has_duplicate_spam = any(count >= 4 for count in counter.values())
    too_many_words = len(text.split()) > 500
    return has_duplicate_spam or unique_ratio < 0.5 or too_many_words


def _score_text(path_label: str, path_is_md: bool, text: str) -> List[Issue]:
    issues: List[Issue] = []
    rel = path_label
    if not text.strip():
        issues.append(Issue(rel, "clarity", "file is empty", ISSUE_WEIGHTS["clarity"]))
        return issues

    if path_is_md and not _has_heading(text):
        issues.append(Issue(rel, "clarity", "markdown file has no heading", ISSUE_WEIGHTS["clarity"]))

    if not _has_verification_guidance(text):
        issues.append(Issue(rel, "verification_instructions", "no verification instructions detected", ISSUE_WEIGHTS["verification_instructions"]))

    for item in _match_any(STALE_PATTERNS, text):
        issues.append(
            Issue(
                rel,
                "stale_references",
                f"possible stale reference marker: {item}",
                ISSUE_WEIGHTS["stale_references"],
            )
        )

    for item in _match_contradictions(text):
        issues.append(Issue(rel, "contradictions", f"possible contradiction: {item}", ISSUE_WEIGHTS["contradictions"]))

    for item in _match_any(DESTRUCTIVE_PATTERNS, text):
        issues.append(
            Issue(
                rel,
                "destructive_permission_language",
                f"destructive command pattern detected: {item}",
                ISSUE_WEIGHTS["destructive_permission_language"],
            )
        )

    for item in _match_any(INJECTION_PATTERNS, text):
        issues.append(Issue(rel, "prompt_injection", f"prompt-injection-prone phrase: {item}", ISSUE_WEIGHTS["prompt_injection"]))

    if _has_repetition(text):
        issues.append(Issue(rel, "repetition", "repetitive or excessively long instruction blocks", ISSUE_WEIGHTS["repetition"]))

    return issues


def score_directory(target_path: str) -> Dict[str, Any]:
    target = Path(target_path).resolve()
    instruction_files = discover_instruction_files(target)
    file_reports: List[Dict[str, Any]] = []
    all_issues: List[Issue] = []

    for file_path in instruction_files:
        file_text = read_file(file_path)
        relative = file_path.relative_to(target).as_posix()
        issues = _score_text(relative, file_path.suffix.lower() == ".md", file_text)
        all_issues.extend(issues)
        file_reports.append(
            {
                "path": relative,
                "size": len(file_text),
                "issues": [issue.to_dict() for issue in issues],
            }
        )

    if not instruction_files:
        all_issues.append(Issue("<none>", "coverage", "no target files were found", ISSUE_WEIGHTS["coverage"]))

    issue_by_category: Dict[str, int] = {}
    deduction = 0.0
    for issue in all_issues:
        issue_by_category.setdefault(issue.category, 0)
        issue_by_category[issue.category] += 1
        deduction += issue.weight

    score = max(0.0, MAX_SCORE - deduction)
    result = {
        "target": str(target),
        "max_score": MAX_SCORE,
        "score": round(score, 2),
        "files": file_reports,
        "issue_count": len(all_issues),
        "issues_by_category": issue_by_category,
        "issues": [issue.to_dict() for issue in all_issues],
    }
    return result


def format_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Agent Context Score",
        "",
        f"- Target: `{report['target']}`",
        f"- Files discovered: {len(report['files'])}",
        f"- Total issues: {report['issue_count']}",
        f"- Overall score: {report['score']}/{report['max_score']}",
        "",
        "## Issues by category",
        "",
    ]
    if report["issues_by_category"]:
        for category in sorted(report["issues_by_category"]):
            lines.append(f"- `{category}`: {report['issues_by_category'][category]}")
    else:
        lines.append("- none")

    lines.extend(["", "## File checks", ""])
    if not report["files"]:
        lines.append("No target files found.")
    else:
        for item in report["files"]:
            lines.append(f"### {item['path']}")
            lines.append(f"- Size: {item['size']} chars")
            if item["issues"]:
                for issue in item["issues"]:
                    lines.append(f"- {issue['category']}: {issue['message']} (−{issue['weight']})")
            else:
                lines.append("- No issues")
            lines.append("")

    if report["issues"]:
        lines.extend(["", "## Top issues", ""])
        for issue in report["issues"]:
            lines.append(f"- {issue['category']} `{issue['path']}`: {issue['message']}")
    return "\n".join(lines).rstrip()


def run_report(target: str, output_format: str) -> str:
    report = score_directory(target)
    if output_format == "json":
        return json.dumps(report, indent=2, sort_keys=True)
    return format_markdown(report)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    target = Path(args.target).resolve()
    if not target.exists():
        raise SystemExit(f"Target path does not exist: {target}")
    if not target.is_dir():
        raise SystemExit(f"Target path is not a directory: {target}")

    report = score_directory(str(target))
    if args.format == "json":
        output = json.dumps(report, indent=2, sort_keys=True)
    else:
        output = format_markdown(report)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")

    print(output)

    if args.fail_under is not None and report["score"] < args.fail_under:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
