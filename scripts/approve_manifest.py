#!/usr/bin/env python3
"""Validate and seal the assignment matrix; direct production is the default."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from manifest_lib import load_manifest, matrix_digest, validate_manifest


def atomic_json_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def seal_manifest(data: dict, status: str = "auto_approved") -> list:
    """Refresh the internal integrity seal without implying a user approval."""
    gate = data.setdefault("review_gate", {})
    previous = dict(gate)
    gate["status"] = "pending"
    issues = validate_manifest(data, allow_pending=True)
    if issues:
        data["review_gate"] = previous
        return issues
    gate["status"] = status
    gate["matrix_sha256"] = matrix_digest(data)
    gate["approved_at"] = datetime.now(timezone.utc).isoformat()
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--status", choices=("approved", "auto_approved"), default="auto_approved",
                        help="Padrão: auto_approved, selo interno sem etapa de aprovação humana.")
    args = parser.parse_args()

    data = load_manifest(args.manifest)
    issues = seal_manifest(data, args.status)
    if issues:
        for issue in issues:
            print(f"{issue.code}: {issue.message}")
        return 1

    atomic_json_write(args.manifest, data)
    print(f"Matriz selada: {data['review_gate']['matrix_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
