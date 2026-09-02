#!/usr/bin/env python3
"""Create Markdown working context with Microsoft MarkItDown."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from manifest_lib import file_sha256
from runtime_support import python_with_modules


TEXT_SUFFIXES = {".md", ".markdown", ".txt"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".heic", ".tif", ".tiff"}


def markitdown_command(suffix: str) -> list[str]:
    python = python_with_modules("markitdown")
    if python:
        return [str(python), "-m", "markitdown"]
    executable = shutil.which("markitdown")
    if executable:
        return [executable]
    raise RuntimeError("Microsoft MarkItDown não está disponível. Execute setup_runtime.py para diagnóstico e autorize --install para a instalação isolada. Não há download implícito.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()

    source = args.input.expanduser().resolve()
    destination = args.output.expanduser().resolve()
    if not source.is_file():
        print(f"Fonte inexistente: {source}", file=sys.stderr)
        return 1
    if source == destination:
        print("A saída não pode sobrescrever o original.", file=sys.stderr)
        return 1
    if source.suffix.lower() in IMAGE_SUFFIXES:
        print(
            "Imagens exigem inspeção visual/OCR do agente; o MarkItDown não é confiável para este formato. "
            "Crie o Markdown manualmente após conferir a imagem.",
            file=sys.stderr,
        )
        return 2

    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        if source.suffix.lower() in TEXT_SUFFIXES:
            temporary.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            try:
                command = [*markitdown_command(source.suffix.lower()), str(source), "-o", str(temporary)]
            except RuntimeError as error:
                print(str(error), file=sys.stderr)
                return 5
            try:
                completed = subprocess.run(command, text=True, capture_output=True, timeout=180)
            except subprocess.TimeoutExpired:
                print("A extração excedeu 180 segundos e foi interrompida.", file=sys.stderr)
                return 4
            if completed.returncode != 0:
                print(completed.stderr or completed.stdout, file=sys.stderr)
                return completed.returncode
        if not temporary.is_file() or temporary.stat().st_size < 20:
            print("A extração ficou vazia ou quase vazia; confira visualmente o original.", file=sys.stderr)
            return 3
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)

    if args.manifest:
        manifest_path = args.manifest.expanduser().resolve()
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        data.setdefault("source", {})["original_path"] = str(source)
        data["source"]["original_sha256"] = file_sha256(source)
        data["source"]["extracted_markdown_path"] = str(destination)
        handle, manifest_tmp_name = tempfile.mkstemp(prefix=f".{manifest_path.name}.", dir=manifest_path.parent)
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            os.replace(manifest_tmp_name, manifest_path)
        except Exception:
            Path(manifest_tmp_name).unlink(missing_ok=True)
            raise
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
