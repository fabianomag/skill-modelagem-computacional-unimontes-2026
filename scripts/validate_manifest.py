#!/usr/bin/env python3
"""Validate a modelagem-computacional-grupo manifest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from manifest_lib import format_matrix_markdown, load_manifest, validate_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--allow-pending", action="store_true")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    parser.add_argument("--matrix", action="store_true", help="Imprime a matriz em Markdown se o manifesto for válido.")
    args = parser.parse_args()

    try:
        data = load_manifest(args.manifest)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"E_MANIFEST_READ: {exc}", file=sys.stderr)
        return 1

    issues = validate_manifest(data, allow_pending=args.allow_pending)
    if args.format == "json":
        print(json.dumps({"ok": not issues, "issues": [issue.as_dict() for issue in issues]}, ensure_ascii=False, indent=2))
    elif issues:
        for issue in issues:
            location = f" [{issue.path}]" if issue.path else ""
            print(f"{issue.code}{location}: {issue.message}", file=sys.stderr)
    else:
        print("Manifesto válido.")

    if not issues and args.matrix:
        print()
        print(format_matrix_markdown(data))
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())

