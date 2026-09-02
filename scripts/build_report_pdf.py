#!/usr/bin/env python3
"""Render a DOCX to QA PNGs and PDF, then record source provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from runtime_support import canonical_renderer, find_libreoffice, python_with_modules, renderer_python


def run_checked(command: list[str], timeout: int = 180) -> None:
    result = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or f"Comando falhou ({result.returncode})").strip())


def render_pdf_pages(pdf: Path, directory: Path) -> None:
    binary = shutil.which("pdftoppm")
    if binary:
        run_checked([binary, "-r", "120", "-png", str(pdf), str(directory / "page")])
        return
    python = python_with_modules("pypdfium2", "PIL")
    if python is None:
        raise RuntimeError("QA visual requer pdftoppm (Poppler) ou pypdfium2 + Pillow. Execute setup_runtime.py para diagnóstico; nada será instalado automaticamente.")
    run_checked([str(python), str(Path(__file__).with_name("render_pdf_pages.py")), str(pdf), str(directory)])


def render_with_libreoffice(docx: Path, directory: Path, temporary_root: Path) -> None:
    libreoffice = find_libreoffice()
    if libreoffice is None:
        raise RuntimeError("LibreOffice não encontrado. Instale-o localmente ou defina LIBREOFFICE_PATH para soffice. O setup não instala aplicativos do sistema.")
    directory.mkdir(parents=True, exist_ok=True)
    profile = temporary_root / "libreoffice-profile"
    run_checked([
        str(libreoffice), f"-env:UserInstallation={profile.as_uri()}",
        "--headless", "--nologo", "--nodefault", "--nofirststartwizard",
        "--convert-to", "pdf:writer_pdf_Export", "--outdir", str(directory), str(docx),
    ])
    rendered_pdf = directory / f"{docx.stem}.pdf"
    if not rendered_pdf.is_file() or rendered_pdf.stat().st_size == 0:
        raise RuntimeError("LibreOffice terminou sem produzir um PDF válido.")
    render_pdf_pages(rendered_pdf, directory)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def update_manifest(manifest_path: Path, docx: Path, pdf: Path) -> None:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    package_root = Path(data["project"]["package_root"]).expanduser().resolve()
    relative_pdf = data["artifacts"]["report"]["pdf"]
    if (package_root / relative_pdf).resolve() != pdf:
        raise ValueError(f"Destino PDF diverge do manifesto: {relative_pdf}")
    provenance = data.setdefault("provenance", {})
    provenance["report_source_sha256_at_pdf_generation"] = sha256(docx)
    provenance.setdefault("generated_pdf_sha256", {})[relative_pdf] = sha256(pdf)
    temporary = manifest_path.with_name(f"{manifest_path.name}.tmp-{os.getpid()}")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(manifest_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("docx", type=Path)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--qa-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--backend", choices=("auto", "codex", "libreoffice"), default="auto")
    args = parser.parse_args()

    docx = args.docx.expanduser().resolve()
    pdf = args.pdf.expanduser().resolve()
    qa_dir = args.qa_dir.expanduser().resolve()
    if not docx.is_file() or docx.suffix.lower() != ".docx":
        parser.error(f"DOCX inexistente ou inválido: {docx}")
    if pdf.suffix.lower() != ".pdf" or pdf == docx:
        parser.error("Informe um destino PDF diferente do DOCX.")
    renderer = canonical_renderer()
    backend = args.backend if args.backend != "auto" else ("codex" if renderer else "libreoffice")
    if backend == "codex" and renderer is None:
        parser.error("render_docx.py não encontrado; use --backend libreoffice ou configure MODELAGEM_DOCX_RENDERER.")
    if args.manifest and not args.manifest.expanduser().is_file():
        parser.error(f"Manifesto inexistente: {args.manifest}")

    qa_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="modelagem-report-") as temporary:
        render_dir = Path(temporary) / "render"
        try:
            if backend == "codex":
                run_checked([str(renderer_python()), str(renderer), str(docx), "--output_dir", str(render_dir), "--emit_pdf"])
            else:
                render_with_libreoffice(docx, render_dir, Path(temporary))
        except (RuntimeError, subprocess.TimeoutExpired) as error:
            print(f"Conversão/QA falhou: {error}", file=sys.stderr)
            return 1
        rendered_pdf = render_dir / f"{docx.stem}.pdf"
        pages = sorted(render_dir.glob("page-*.png"))
        if not rendered_pdf.is_file() or rendered_pdf.stat().st_size == 0 or not pages:
            print("O renderizador não produziu PDF e PNGs íntegros.", file=sys.stderr)
            return 1
        pdf.parent.mkdir(parents=True, exist_ok=True)
        temporary_pdf = pdf.with_name(f".{pdf.name}.tmp-{os.getpid()}")
        shutil.copy2(rendered_pdf, temporary_pdf)
        temporary_pdf.replace(pdf)
        for stale in qa_dir.glob("page-*.png"):
            stale.unlink()
        for page in pages:
            shutil.copy2(page, qa_dir / page.name)

    if args.manifest:
        manifest = args.manifest.expanduser().resolve()
        if not manifest.is_file():
            parser.error(f"Manifesto inexistente: {manifest}")
        update_manifest(manifest, docx, pdf)
    print(json.dumps({"output": str(pdf), "backend": backend, "qa_pages": len(list(qa_dir.glob('page-*.png')))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
