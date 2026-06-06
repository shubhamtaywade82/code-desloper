#!/usr/bin/env python3
"""
Code Deslopper — Smell Detector Script
Scans a codebase for common AI-generated slop patterns.
Outputs a JSON smell report for Phase 1 detection.

Usage:
    python smell-detector.py <path> [--ext rb,js,ts,jsx,tsx,py,go]
"""

import os
import re
import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Pattern definitions by language
PATTERNS = {
    "ruby": {
        "trivial_service": re.compile(
            r'class\s+(\w+Service)\s*<\s*\w*\s*\n.*?def\s+(self\.)?call\s*\(.*\).*?\n.*?\bend\b',
            re.DOTALL
        ),
        "fake_inheritance": re.compile(
            r'class\s+\w+Service\s*<\s+(BaseService|ApplicationService)',
            re.MULTILINE
        ),
        "empty_concern": re.compile(
            r'module\s+(\w+Concern)\s*\n.*?extend\s+ActiveSupport::Concern',
            re.DOTALL
        ),
        "verb_inflation": re.compile(
            r'\b(do_process|execute_action|perform_task|run_operation|handle_request)\b'
        ),
        "enterprise_suffix": re.compile(
            r'class\s+\w+(Manager|Processor|Handler|Coordinator|Executor)\b'
        ),
        "explicit_return": re.compile(r'\breturn\s+.*?\n\s*end\b', re.MULTILINE),
        "hash_rocket": re.compile(r':\w+\s*=>'),
        "missing_frozen_string": re.compile(r'^(?!#\s*frozen_string_literal:\s*true)', re.MULTILINE),
    },
    "js_ts": {
        "one_method_class": re.compile(
            r'class\s+(\w+Manager|\w+Service|\w+Handler)\s*\{[^}]*?\b(async\s+)?\w+\s*\([^)]*\)\s*\{[^}]*\}[^}]*\}',
            re.DOTALL
        ),
        "redundant_memo": re.compile(
            r'useMemo\s*\(\s*\(\s*\)\s*=>\s*\{[^}]*\}\s*,\s*\[\s*\]\s*\)'
        ),
        "nested_if_pyramid": re.compile(
            r'if\s*\([^)]*\)\s*\{[^}]*if\s*\([^)]*\)\s*\{[^}]*if\s*\([^)]*\)',
            re.DOTALL
        ),
        "any_type": re.compile(r':\s*any\b'),
        "empty_wrapper_component": re.compile(
            r'const\s+(\w+)\s*=\s*\(\s*\{\s*children\s*\}\s*\)\s*=>\s*<\w+[^>]*>\{children\}</\w+>'
        ),
    },
    "python": {
        "abc_overkill": re.compile(r'class\s+\w+\s*\(\s*ABC\s*\)\s*:'),
        "non_idiomatic_loop": re.compile(r'for\s+\w+\s+in\s+range\s*\(\s*len\s*\('),
        "truthiness_check": re.compile(r'if\s+.*==\s+(True|False):'),
        "len_check": re.compile(r'if\s+len\s*\(\s*.*\s*\)\s*>\s*0:'),
        "todo_scaffolding": re.compile(r'#\s*TODO'),
    },
    "go": {
        "premature_interface": re.compile(r'type\s+\w+\s+interface\s*\{'),
        "redundant_pointer": re.compile(r'\*(string|int|bool|float64)'),
        "else_after_return": re.compile(r'if\s+err\s*!=\s*nil\s*\{[^}]*return[^}]*\}\s*else\s*\{'),
    }
}


def detect_smells(file_path: Path, content: str) -> List[Dict[str, Any]]:
    """Detect smells in a single file."""
    smells = []
    ext = file_path.suffix.lower()
    lang = (
        "ruby" if ext in (".rb",)
        else "js_ts" if ext in (".js", ".ts", ".jsx", ".tsx")
        else "python" if ext in (".py",)
        else "go" if ext in (".go",)
        else None
    )

    if not lang:
        return smells

    patterns = PATTERNS[lang]
    lines = content.splitlines()

    for name, pattern in patterns.items():
        for match in pattern.finditer(content):
            line_num = content[:match.start()].count("\n") + 1
            context = lines[max(0, line_num-2):line_num+1]

            # Risk scoring
            risk = 1
            if lang == "ruby" and ("callback" in content.lower() or "before_save" in content or "before_action" in content):
                risk = 4
            elif name in ("trivial_service", "one_method_class", "empty_wrapper_component", "abc_overkill", "premature_interface"):
                risk = 2
            elif name in ("nested_if_pyramid", "else_after_return"):
                risk = 2
            elif name == "fake_inheritance":
                risk = 3

            smells.append({
                "file": str(file_path),
                "line": line_num,
                "category": name,
                "risk": risk,
                "match": match.group(0)[:120],
                "context": "\n".join(context),
                "action": "ask" if risk >= 3 else "refactor"
            })

    return smells


def scan_directory(path: Path, extensions: List[str]) -> List[Dict[str, Any]]:
    """Recursively scan directory for smell patterns."""
    all_smells = []

    for ext in extensions:
        for file_path in path.rglob(f"*.{ext}"):
            if "node_modules" in str(file_path) or "vendor" in str(file_path) or ".git" in str(file_path):
                continue
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                smells = detect_smells(file_path, content)
                all_smells.extend(smells)
            except Exception as e:
                print(f"Error reading {file_path}: {e}", file=sys.stderr)

    return all_smells


def main():
    parser = argparse.ArgumentParser(description="Code Deslopper Smell Detector")
    parser.add_argument("path", help="Directory or file to scan")
    parser.add_argument("--ext", default="rb,js,ts,jsx,tsx,py,go", help="Comma-separated extensions")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    target = Path(args.path)
    extensions = [e.strip().lstrip(".") for e in args.ext.split(",")]

    if target.is_file():
        content = target.read_text(encoding="utf-8", errors="ignore")
        smells = detect_smells(target, content)
    else:
        smells = scan_directory(target, extensions)

    # Sort by risk (descending)
    smells.sort(key=lambda x: x["risk"], reverse=True)

    if args.json:
        print(json.dumps({"smells": smells, "total": len(smells)}, indent=2))
    else:
        print(f"Found {len(smells)} smell(s)\n")
        for s in smells:
            risk_label = "🔴" if s["risk"] >= 4 else "🟡" if s["risk"] == 3 else "🟢"
            print(f"{risk_label} [{s['risk']}/5] {s['category']} at {s['file']}:{s['line']}")
            print(f"   Match: {s['match'][:80]}...")
            print(f"   Action: {s['action']}\n")


if __name__ == "__main__":
    main()
