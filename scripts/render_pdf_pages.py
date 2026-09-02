#!/usr/bin/env python3
"""Render PDF pages for visual inspection without a system Poppler installation."""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--dpi", type=int, default=120)
    args = parser.parse_args()
    if not args.pdf.is_file() or not 72 <= args.dpi <= 300:
        parser.error("Informe um PDF existente e DPI entre 72 e 300.")
    import pypdfium2 as pdfium

    args.output_dir.mkdir(parents=True, exist_ok=True)
    document = pdfium.PdfDocument(str(args.pdf))
    try:
        for index in range(len(document)):
            page = document[index]
            bitmap = page.render(scale=args.dpi / 72)
            try:
                bitmap.to_pil().save(args.output_dir / f"page-{index + 1}.png")
            finally:
                bitmap.close()
                page.close()
    finally:
        document.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
