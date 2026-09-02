#!/usr/bin/env python3
"""Validate a final modelagem-computacional-grupo package.

The manifest validator owns the assignment matrix.  This module adds checks
that require the generated public tree: artifact presence, provenance hashes,
deck/PDF parity, conditional deliverables, canonical facts and the minimum
content promised by each individual minute.

Only the Python standard library is required.  Poppler's ``pdfinfo`` and
``pdftotext`` are used when available because reliable text extraction from a
general PDF is outside the scope of the standard library.  A deliberately
small fallback handles simple, uncompressed PDFs used by the unit tests.
"""

from __future__ import annotations

import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
import zipfile
import xml.etree.ElementTree as ET

from manifest_lib import (
    Issue,
    file_sha256,
    load_manifest,
    question_text,
    validate_manifest,
)


CODE_SUFFIXES = {
    ".c",
    ".cc",
    ".cpp",
    ".ipynb",
    ".jl",
    ".m",
    ".py",
    ".r",
    ".R",
}
FORBIDDEN_PUBLIC_DIRS = {"tmp", ".modelagem-build", "__pycache__"}
REMOTE_URL_RE = re.compile(r"^(?:https?:)?//", re.IGNORECASE)
PDF_PAGE_RE = re.compile(rb"/Type\s*/Page(?!s)\b")
PDF_LITERAL_RE = re.compile(rb"\(((?:\\.|[^\\)])*)\)\s*T[jJ]")
DRAFT_MARKERS = (
    "[Título do problema]",
    "[Apresente o problema",
    "[Decisão final somente após os testes.]",
    "[Reproduza fielmente o enunciado",
    "[equação central e definição de símbolos]",
    "[Forma, parâmetros, hipótese e resultado verificado.]",
    "[Duplique esta subseção para cada família realmente comparada.",
    "[Mostre previsões, resíduos, métricas",
    "[Combine aderência ao problema",
    "[Use o modelo escolhido",
    "[Responda objetivamente às perguntas",
    "[Declare faixa válida",
)


@dataclass(frozen=True)
class ParsedSlide:
    slide_id: str
    owner_block_id: str
    title: str


def _normalise_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", html.unescape(value or ""))
    value = value.replace("\u00a0", " ").replace("\u200b", "")
    return " ".join(value.split()).casefold()


def _contains(text: str, expected: str) -> bool:
    return _normalise_text(expected) in _normalise_text(text)


def _safe_artifact_path(package: Path, relative: Any) -> Path | None:
    if not isinstance(relative, str) or not relative.strip():
        return None
    candidate = (package / relative).resolve()
    try:
        candidate.relative_to(package.resolve())
    except ValueError:
        return None
    return candidate


def _find_poppler_binary(name: str) -> str | None:
    direct = shutil.which(name)
    if direct:
        return direct
    pdfinfo = shutil.which("pdfinfo")
    if pdfinfo:
        candidate = Path(pdfinfo).resolve().parent.parent.parent / "native" / "poppler" / "poppler" / "bin" / name
        if candidate.is_file():
            return str(candidate)
        # Codex's pdfinfo wrapper is not a symlink, so derive from its visible path too.
        visible = Path(pdfinfo)
        candidate = visible.parent.parent.parent / "native" / "poppler" / "poppler" / "bin" / name
        if candidate.is_file():
            return str(candidate)
    return None


def _run_text(command: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.decode("utf-8", errors="replace")


def pdf_page_count(path: Path) -> int | None:
    binary = _find_poppler_binary("pdfinfo")
    if binary:
        output = _run_text([binary, str(path)])
        if output:
            match = re.search(r"^Pages:\s*(\d+)\s*$", output, re.MULTILINE)
            if match:
                return int(match.group(1))
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    count = len(PDF_PAGE_RE.findall(raw))
    return count or None


def _decode_pdf_literal(raw: bytes) -> str:
    result = bytearray()
    index = 0
    escapes = {
        ord("n"): ord("\n"),
        ord("r"): ord("\r"),
        ord("t"): ord("\t"),
        ord("b"): ord("\b"),
        ord("f"): ord("\f"),
        ord("("): ord("("),
        ord(")"): ord(")"),
        ord("\\"): ord("\\"),
    }
    while index < len(raw):
        current = raw[index]
        if current != ord("\\"):
            result.append(current)
            index += 1
            continue
        index += 1
        if index >= len(raw):
            break
        escaped = raw[index]
        if escaped in escapes:
            result.append(escapes[escaped])
            index += 1
            continue
        if ord("0") <= escaped <= ord("7"):
            end = index
            while end < min(index + 3, len(raw)) and ord("0") <= raw[end] <= ord("7"):
                end += 1
            result.append(int(raw[index:end], 8))
            index = end
            continue
        if escaped in {ord("\n"), ord("\r")}:
            index += 1
            if escaped == ord("\r") and index < len(raw) and raw[index] == ord("\n"):
                index += 1
            continue
        result.append(escaped)
        index += 1
    try:
        return result.decode("utf-8")
    except UnicodeDecodeError:
        return result.decode("latin-1", errors="replace")


def _fallback_pdf_pages(path: Path) -> list[str]:
    try:
        raw = path.read_bytes()
    except OSError:
        return []
    starts = [match.start() for match in PDF_PAGE_RE.finditer(raw)]
    if not starts:
        return []
    pages: list[str] = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(raw)
        literals = [_decode_pdf_literal(match.group(1)) for match in PDF_LITERAL_RE.finditer(raw[start:end])]
        pages.append(" ".join(literals))
    return pages


def extract_pdf_pages(path: Path) -> list[str]:
    binary = _find_poppler_binary("pdftotext")
    if binary:
        output = _run_text([binary, "-layout", str(path), "-"])
        if output is not None:
            pages = [page for page in output.split("\f") if page.strip()]
            if pages:
                return pages
    return _fallback_pdf_pages(path)


def extract_pdf_text(path: Path) -> str:
    return "\n\f\n".join(extract_pdf_pages(path))


def extract_docx_text(path: Path) -> str:
    chunks: list[str] = []
    try:
        with zipfile.ZipFile(path) as archive:
            names = [
                name
                for name in archive.namelist()
                if name == "word/document.xml"
                or re.fullmatch(r"word/(?:header|footer)\d+\.xml", name)
                or name in {"word/footnotes.xml", "word/endnotes.xml"}
            ]
            for name in sorted(names):
                try:
                    root = ET.fromstring(archive.read(name))
                except (KeyError, ET.ParseError):
                    continue
                for element in root.iter():
                    local = element.tag.rsplit("}", 1)[-1]
                    if local == "t" and element.text:
                        chunks.append(element.text)
                    elif local in {"p", "br", "tab"}:
                        chunks.append("\n" if local != "tab" else "\t")
    except (OSError, zipfile.BadZipFile):
        return ""
    return " ".join(chunks)


class _DeckHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.slides: list[ParsedSlide] = []
        self.remote_resources: list[str] = []
        self._slide: dict[str, str] | None = None
        self._title_tag: str | None = None
        self._title_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        classes = set(attributes.get("class", "").split())
        if tag == "section" and "slide" in classes:
            self._slide = {
                "id": attributes.get("data-slide-id", ""),
                "owner": attributes.get("data-owner-block-id", ""),
            }
            self._title_chunks = []
        elif self._slide is not None and tag in {"h1", "h2"} and self._title_tag is None:
            self._title_tag = tag
            self._title_chunks = []

        resource_attribute: str | None = None
        if tag in {"script", "img", "iframe", "audio", "video", "source"}:
            resource_attribute = "src"
        elif tag == "link" and attributes.get("rel", "").lower() in {"stylesheet", "preload", "modulepreload"}:
            resource_attribute = "href"
        elif tag == "object":
            resource_attribute = "data"
        if resource_attribute:
            value = attributes.get(resource_attribute, "")
            if REMOTE_URL_RE.match(value):
                self.remote_resources.append(value)
        poster = attributes.get("poster", "")
        if poster and REMOTE_URL_RE.match(poster):
            self.remote_resources.append(poster)

    def handle_data(self, data: str) -> None:
        if self._title_tag is not None:
            self._title_chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._title_tag == tag:
            self._title_tag = None
        if tag == "section" and self._slide is not None:
            self.slides.append(
                ParsedSlide(
                    slide_id=self._slide["id"],
                    owner_block_id=self._slide["owner"],
                    title=" ".join("".join(self._title_chunks).split()),
                )
            )
            self._slide = None
            self._title_tag = None
            self._title_chunks = []


def parse_deck_html(path: Path) -> tuple[list[ParsedSlide], list[str], str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return [], [], ""
    parser = _DeckHTMLParser()
    try:
        parser.feed(text)
    except Exception:
        return [], [], text
    return parser.slides, parser.remote_resources, text


def parse_deck_data(path: Path) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    assignment = re.search(r"window\.MODELAGEM_DECK\s*=\s*(\{[\s\S]*\})\s*;?\s*$", text)
    if assignment:
        try:
            payload = json.loads(assignment.group(1))
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict) and isinstance(payload.get("slides"), list):
            parsed = []
            for slide in payload["slides"]:
                if not isinstance(slide, dict) or not isinstance(slide.get("id"), str):
                    continue
                parsed.append(
                    {
                        "id": slide.get("id"),
                        "owner_block_id": slide.get("ownerBlockId"),
                        "owner_name": slide.get("ownerName"),
                        "title": slide.get("title"),
                        "seconds": slide.get("seconds"),
                    }
                )
            return parsed

    objects = re.findall(r"\{([^{}]*(?:['\"]?id['\"]?)\s*:\s*['\"]S\d+['\"][^{}]*)\}", text, re.DOTALL)
    parsed: list[dict[str, Any]] = []
    for body in objects:
        record: dict[str, Any] = {}
        for target, source in (
            ("id", "id"),
            ("owner_block_id", "ownerBlockId"),
            ("owner_name", "ownerName"),
            ("title", "title"),
        ):
            match = re.search(rf"(?:['\"]?{source}['\"]?)\s*:\s*(['\"])(.*?)\1", body, re.DOTALL)
            if match:
                record[target] = match.group(2)
        seconds = re.search(r"(?:['\"]?seconds['\"]?)\s*:\s*(\d+)", body)
        if seconds:
            record["seconds"] = int(seconds.group(1))
        if record.get("id"):
            parsed.append(record)
    return parsed


def compute_bundle_sha256(package: Path, declared_paths: Iterable[str]) -> str:
    presentation_root = package / "Entregaveis" / "Apresentacao"
    relative_paths: set[Path] = {
        path.relative_to(presentation_root)
        for path in presentation_root.rglob("*")
        if path.is_file() and path.suffix.casefold() != ".pdf"
    }
    digest = hashlib.sha256()
    for relative in sorted(relative_paths, key=lambda item: item.as_posix()):
        absolute = presentation_root / relative
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        with absolute.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def _fact_display(fact: dict[str, Any], kind: str) -> list[str]:
    formats = fact.get("formats") if isinstance(fact.get("formats"), dict) else {}
    value = formats.get(kind)
    if value is None and kind == "understanding":
        value = formats.get("guide")
    if value is None and kind == "presentation_minute":
        value = formats.get("slide")
    if isinstance(value, str) and value.strip():
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item.strip()]
    canonical = fact.get("value")
    unit = fact.get("unit")
    if canonical is None:
        return []
    rendered = str(canonical)
    if isinstance(unit, str) and unit.strip():
        rendered = f"{rendered} {unit}"
    return [rendered]


def _validate_facts(
    issues: list[Issue],
    text: str,
    fact_ids: Iterable[str],
    facts: dict[str, dict[str, Any]],
    kind: str,
    artifact: str,
) -> None:
    for fact_id in sorted(set(fact_ids)):
        fact = facts.get(fact_id)
        if fact is None:
            issues.append(Issue("E_FACT_REFERENCE", f"Fato inexistente: {fact_id}.", artifact))
            continue
        displays = _fact_display(fact, kind)
        if not displays:
            issues.append(Issue("E_FACT_FORMAT", f"Fato {fact_id} não possui valor ou formato utilizável.", artifact))
            continue
        if not any(_contains(text, display) for display in displays):
            issues.append(
                Issue(
                    "E_FACT_MISMATCH",
                    f"{artifact} não contém o valor canônico de {fact_id}: {' ou '.join(displays)}.",
                    artifact,
                )
            )


def _require_text(issues: list[Issue], text: str, expected: str, artifact: str, label: str) -> None:
    if expected and not _contains(text, expected):
        issues.append(Issue("E_MINUTE_CONTENT", f"{artifact} não contém {label}: {expected}.", artifact))


def validate_package(data: dict[str, Any], package: Path | None = None) -> list[Issue]:
    issues = list(validate_manifest(data))
    if issues:
        return issues

    package = (package or Path(data["project"]["package_root"])).expanduser().resolve()
    if not package.is_dir():
        return [Issue("E_PACKAGE_MISSING", f"Pacote inexistente: {package}.", str(package))]

    artifacts = data["artifacts"]
    presentation = artifacts["presentation"]
    report = artifacts["report"]
    source_bundle = presentation.get("source_bundle", [])

    declared_paths: set[str] = {
        report["source_docx"],
        report["pdf"],
        presentation["html_entry"],
        presentation["pdf"],
        artifacts["study_guide"]["pdf"],
    }
    declared_paths.update(path for path in source_bundle if isinstance(path, str))
    for minute in artifacts["minutes"]:
        declared_paths.add(minute["understanding_pdf"])
        declared_paths.add(minute["presentation_pdf"])

    resolved: dict[str, Path] = {}
    for relative in sorted(declared_paths):
        target = _safe_artifact_path(package, relative)
        if target is None:
            issues.append(Issue("E_ARTIFACT_PATH", f"Caminho sai do pacote: {relative}.", relative))
        elif not target.is_file():
            issues.append(Issue("E_ARTIFACT_MISSING", f"Artefato ausente: {relative}.", relative))
        else:
            resolved[relative] = target

    public_files = [path for path in package.rglob("*") if path.is_file()]
    for directory in [path for path in package.rglob("*") if path.is_dir()]:
        if directory.name in FORBIDDEN_PUBLIC_DIRS:
            issues.append(Issue("E_PUBLIC_TEMP", f"Diretório temporário público: {directory.relative_to(package)}.", str(directory)))
    for path in public_files:
        relative = path.relative_to(package)
        if path.suffix.casefold() in {".md", ".markdown"}:
            issues.append(Issue("E_PUBLIC_MARKDOWN", f"Markdown público não permitido: {relative}.", relative.as_posix()))

    zip_files = [path for path in public_files if path.suffix.casefold() == ".zip"]
    zip_requested = bool(data["delivery"].get("zip", {}).get("requested"))
    if zip_requested and len(zip_files) != 1:
        issues.append(Issue("E_ZIP_POLICY", "ZIP solicitado exige exatamente um arquivo ZIP no pacote.", "delivery.zip"))
    if not zip_requested and zip_files:
        issues.append(Issue("E_ZIP_POLICY", "O pacote contém ZIP não solicitado.", "delivery.zip"))

    source = data.get("source", {})
    original = Path(source.get("original_path", "")).expanduser()
    recorded_source_hash = source.get("original_sha256")
    actual_source_hash: str | None = None
    if not original.is_file():
        issues.append(Issue("E_SOURCE_MISSING", f"Original não encontrado: {original}.", "source.original_path"))
    else:
        actual_source_hash = file_sha256(original)
        if not isinstance(recorded_source_hash, str) or not recorded_source_hash:
            issues.append(Issue("E_SOURCE_HASH", "O SHA-256 do original não foi registrado.", "source.original_sha256"))
        elif recorded_source_hash != actual_source_hash:
            issues.append(Issue("E_SOURCE_HASH", "O original mudou desde a extração.", "source.original_sha256"))
    if actual_source_hash:
        for path in public_files:
            try:
                if file_sha256(path) == actual_source_hash:
                    issues.append(Issue("E_SOURCE_COPY", f"O original foi duplicado no pacote: {path.relative_to(package)}.", str(path)))
            except OSError:
                continue

    code_root = package / "Entregaveis" / "Codigo"
    code_policy = data["delivery"]["code"]
    if code_policy["include"]:
        code_files = [path for path in code_root.rglob("*") if path.is_file()] if code_root.is_dir() else []
        if not any(path.suffix in CODE_SUFFIXES for path in code_files):
            issues.append(Issue("E_CODE_POLICY", "Código obrigatório, mas nenhum arquivo executável foi encontrado.", str(code_root)))
        requirements = code_root / "requirements.txt"
        dependencies = code_policy.get("external_dependencies", [])
        if dependencies and not requirements.is_file():
            issues.append(Issue("E_CODE_REQUIREMENTS", "Dependências externas exigem requirements.txt.", str(requirements)))
        elif dependencies and requirements.is_file():
            requirement_text = requirements.read_text(encoding="utf-8", errors="replace")
            for dependency in dependencies:
                package_name = str(dependency).split("=", 1)[0].split("<", 1)[0].split(">", 1)[0].strip()
                if package_name and package_name.casefold() not in requirement_text.casefold():
                    issues.append(Issue("E_CODE_REQUIREMENTS", f"Dependência ausente em requirements.txt: {dependency}.", str(requirements)))
        elif not dependencies and requirements.is_file():
            issues.append(Issue("E_CODE_REQUIREMENTS", "requirements.txt existe sem dependências externas declaradas.", str(requirements)))
    elif code_root.exists():
        issues.append(Issue("E_CODE_POLICY", "A pasta Codigo existe, mas o manifesto não autoriza código.", str(code_root)))

    # Reject undeclared files except dynamic presentation assets, conditional code and the requested ZIP.
    for path in public_files:
        relative = path.relative_to(package)
        relative_posix = relative.as_posix()
        allowed_dynamic = (
            relative.parts[:3] == ("Entregaveis", "Apresentacao", "assets")
            or (data["delivery"]["code"]["include"] and relative.parts[:2] == ("Entregaveis", "Codigo"))
            or (zip_requested and path.suffix.casefold() == ".zip")
        )
        if relative_posix not in declared_paths and not allowed_dynamic:
            issues.append(Issue("E_PUBLIC_EXTRA", f"Arquivo público não declarado: {relative_posix}.", relative_posix))

    if issues and any(issue.code in {"E_ARTIFACT_MISSING", "E_ARTIFACT_PATH"} for issue in issues):
        return issues

    report_docx = resolved[report["source_docx"]]
    report_pdf = resolved[report["pdf"]]
    deck_html = resolved[presentation["html_entry"]]
    deck_pdf = resolved[presentation["pdf"]]
    guide_pdf = resolved[artifacts["study_guide"]["pdf"]]

    report_hash = file_sha256(report_docx)
    if data.get("provenance", {}).get("report_source_sha256_at_pdf_generation") != report_hash:
        issues.append(Issue("E_STALE_REPORT_PDF", "O PDF do relatório não corresponde ao DOCX atual.", report["pdf"]))
    bundle_hash = compute_bundle_sha256(package, source_bundle)
    if data.get("provenance", {}).get("presentation_bundle_sha256_at_pdf_generation") != bundle_hash:
        issues.append(Issue("E_STALE_PRESENTATION_PDF", "O PDF da apresentação não corresponde ao bundle HTML atual.", presentation["pdf"]))
    for relative, expected_hash in data.get("provenance", {}).get("generated_pdf_sha256", {}).items():
        target = _safe_artifact_path(package, relative)
        if target is None or not target.is_file() or file_sha256(target) != expected_hash:
            issues.append(Issue("E_GENERATED_PDF_HASH", f"PDF alterado ou ausente: {relative}.", relative))
    for relative, record in data.get("provenance", {}).get("study_sources", {}).items():
        if not isinstance(record, dict):
            issues.append(Issue("E_STALE_STUDY_PDF", f"Proveniência inválida: {relative}.", relative))
            continue
        source_path = Path(str(record.get("source_path", ""))).expanduser()
        expected_source_hash = record.get("source_sha256")
        if not source_path.is_file() or file_sha256(source_path) != expected_source_hash:
            issues.append(Issue("E_STALE_STUDY_PDF", f"O PDF de estudo está obsoleto: {relative}.", relative))

    pdf_paths = [report_pdf, deck_pdf, guide_pdf]
    pdf_paths.extend(
        resolved[path]
        for minute in artifacts["minutes"]
        for path in (minute["understanding_pdf"], minute["presentation_pdf"])
    )
    for pdf_path in pdf_paths:
        count = pdf_page_count(pdf_path)
        if count is None or count < 1:
            issues.append(Issue("E_PDF_INVALID", f"PDF sem páginas legíveis: {pdf_path.relative_to(package)}.", str(pdf_path)))

    manifest_slides = sorted(data["slides"], key=lambda item: item["ordinal"])
    parsed_slides, remote_resources, html_text = parse_deck_html(deck_html)
    expected_ids = [slide["id"] for slide in manifest_slides]
    if parsed_slides:
        actual_ids = [slide.slide_id for slide in parsed_slides]
        if actual_ids != expected_ids:
            issues.append(Issue("E_HTML_SLIDE_IDS", f"IDs/ordem do HTML {actual_ids} diferem do manifesto {expected_ids}.", presentation["html_entry"]))
        for manifest_slide, parsed_slide in zip(manifest_slides, parsed_slides):
            if parsed_slide.owner_block_id != manifest_slide["owner_block_id"]:
                issues.append(Issue("E_HTML_SLIDE_OWNER", f"Proprietário divergente no slide {manifest_slide['id']}.", presentation["html_entry"]))
            if _normalise_text(parsed_slide.title) != _normalise_text(manifest_slide["title"]):
                issues.append(Issue("E_HTML_SLIDE_TITLE", f"Título divergente no slide {manifest_slide['id']}.", presentation["html_entry"]))
    elif 'id="stage"' not in html_text or "deck-data.js" not in html_text or "deck.js" not in html_text:
        issues.append(Issue("E_HTML_SLIDE_IDS", "O HTML dinâmico não possui palco ou scripts do deck.", presentation["html_entry"]))
    if remote_resources:
        issues.append(Issue("E_OFFLINE_RESOURCE", f"Recursos remotos no deck: {', '.join(remote_resources)}.", presentation["html_entry"]))
    for relative in source_bundle:
        target = resolved.get(relative)
        if not target or target.suffix.casefold() not in {".css", ".js", ".html"}:
            continue
        content = target.read_text(encoding="utf-8", errors="replace")
        if target.suffix.casefold() == ".css" and re.search(r"url\(\s*['\"]?(?:https?:)?//", content, re.IGNORECASE):
            issues.append(Issue("E_OFFLINE_RESOURCE", f"Recurso remoto em {relative}.", relative))
        if target.suffix.casefold() == ".js" and re.search(r"(?:import\s+(?:[^;]+?\s+from\s+)?|import\()\s*['\"](?:https?:)?//", content, re.IGNORECASE):
            issues.append(Issue("E_OFFLINE_RESOURCE", f"Import remoto em {relative}.", relative))
        if re.search(r"\{\{[A-Z0-9_]+\}\}", content):
            issues.append(Issue("E_PLACEHOLDER", f"Placeholder não resolvido em {relative}.", relative))

    deck_data_path = next((resolved[path] for path in source_bundle if Path(path).name == "deck-data.js" and path in resolved), None)
    deck_records = parse_deck_data(deck_data_path) if deck_data_path else []
    if len(deck_records) != len(manifest_slides):
        issues.append(Issue("E_DECK_DATA", "deck-data.js não possui a mesma quantidade de slides do manifesto.", "deck-data.js"))
    else:
        block_to_member = {block["id"]: block["member_id"] for block in data["blocks"]}
        people = {member["id"]: member["name"] for member in data["team"]}
        for expected, actual in zip(manifest_slides, deck_records):
            expected_member = people[block_to_member[expected["owner_block_id"]]]
            if actual.get("id") != expected["id"] or actual.get("owner_block_id") != expected["owner_block_id"]:
                issues.append(Issue("E_DECK_DATA", f"ID ou proprietário divergente em {expected['id']}.", "deck-data.js"))
            if actual.get("owner_name") != expected_member:
                issues.append(Issue("E_DECK_DATA", f"Nome do apresentador divergente em {expected['id']}.", "deck-data.js"))
            if _normalise_text(actual.get("title", "")) != _normalise_text(expected["title"]):
                issues.append(Issue("E_DECK_DATA", f"Título divergente em {expected['id']}.", "deck-data.js"))
            if actual.get("seconds") != expected["seconds"]:
                issues.append(Issue("E_DECK_DATA", f"Tempo divergente em {expected['id']}.", "deck-data.js"))

    deck_pages = pdf_page_count(deck_pdf)
    if deck_pages != len(manifest_slides):
        issues.append(Issue("E_HTML_PDF_PARITY", f"HTML possui {len(manifest_slides)} slides e PDF possui {deck_pages} páginas.", presentation["pdf"]))
    extracted_deck_pages = extract_pdf_pages(deck_pdf)
    if len(extracted_deck_pages) != len(manifest_slides):
        issues.append(Issue("E_PDF_TEXT_UNAVAILABLE", "Não foi possível conferir o texto página a página da apresentação.", presentation["pdf"]))
    else:
        for expected, page_text in zip(manifest_slides, extracted_deck_pages):
            if not _contains(page_text, expected["title"]):
                issues.append(Issue("E_HTML_PDF_PARITY", f"Título de {expected['id']} ausente na página correspondente do PDF.", presentation["pdf"]))

    facts = {
        fact["id"]: fact
        for fact in data.get("facts", [])
        if isinstance(fact, dict) and isinstance(fact.get("id"), str)
    }
    report_fact_ids = report.get("required_fact_ids", [])
    report_text = extract_docx_text(report_docx)
    report_pdf_text = extract_pdf_text(report_pdf)
    if not report_text:
        issues.append(Issue("E_DOCX_TEXT", "Não foi possível extrair texto do relatório DOCX.", report["source_docx"]))
    if not report_pdf_text:
        issues.append(Issue("E_PDF_TEXT_UNAVAILABLE", "Não foi possível extrair texto do relatório PDF.", report["pdf"]))
    for marker in DRAFT_MARKERS:
        if marker in report_text or marker in report_pdf_text:
            issues.append(Issue("E_DRAFT_CONTENT", f"O relatório ainda contém instrução de template: {marker}", report["source_docx"]))
    _validate_facts(issues, report_text, report_fact_ids, facts, "report", report["source_docx"])
    _validate_facts(issues, report_pdf_text, report_fact_ids, facts, "report", report["pdf"])

    slide_fact_ids = [fact_id for slide in manifest_slides for fact_id in slide.get("fact_ids", [])]
    deck_source_text = html_text
    if deck_data_path:
        deck_source_text += "\n" + deck_data_path.read_text(encoding="utf-8", errors="replace")
    _validate_facts(issues, deck_source_text, slide_fact_ids, facts, "slide", presentation["html_entry"])
    _validate_facts(issues, "\n".join(extracted_deck_pages), slide_fact_ids, facts, "slide", presentation["pdf"])

    guide_text = extract_pdf_text(guide_pdf)
    if not guide_text:
        issues.append(Issue("E_PDF_TEXT_UNAVAILABLE", "Não foi possível extrair texto do guia central.", artifacts["study_guide"]["pdf"]))
    for expected in ("Entrada", "Saída", "Perguntas", "Glossário"):
        if not _contains(guide_text, expected):
            issues.append(Issue("E_GUIDE_CONTENT", f"Guia central não contém a seção conceitual: {expected}.", artifacts["study_guide"]["pdf"]))
    for question in data["problem"]["questions"]:
        if not _contains(guide_text, question_text(question)):
            issues.append(Issue("E_GUIDE_CONTENT", f"Guia central não reproduz {question['id']}.", artifacts["study_guide"]["pdf"]))
        if question.get("origin") == "derived" and not _contains(guide_text, "Objetivo derivado"):
            issues.append(Issue("E_GUIDE_CONTENT", "Objetivos inferidos devem ser identificados como objetivo derivado, não pergunta original.", artifacts["study_guide"]["pdf"]))
    guide_fact_ids = set(report_fact_ids)
    for block in data["blocks"]:
        guide_fact_ids.update(block.get("fact_ids", []))
    _validate_facts(issues, guide_text, guide_fact_ids, facts, "guide", artifacts["study_guide"]["pdf"])

    units = {unit["id"]: unit for unit in data["problem"]["question_units"]}
    questions = {question["id"]: question for question in data["problem"]["questions"]}
    sections = {section["id"]: section for section in data["guide"]["sections"]}
    glossary = {term["id"]: term for term in data["guide"].get("glossary_terms", [])}
    blocks_by_member = {block["member_id"]: block for block in data["blocks"]}
    slides_by_id = {slide["id"]: slide for slide in data["slides"]}
    minute_entries = {minute["member_id"]: minute for minute in artifacts["minutes"]}
    for member in data["team"]:
        member_id, member_name = member["id"], member["name"]
        block = blocks_by_member[member_id]
        minute = minute_entries[member_id]
        understanding_path = resolved[minute["understanding_pdf"]]
        presentation_path = resolved[minute["presentation_pdf"]]
        understanding_text = extract_pdf_text(understanding_path)
        presentation_text = extract_pdf_text(presentation_path)
        if not understanding_text:
            issues.append(Issue("E_PDF_TEXT_UNAVAILABLE", f"Não foi possível ler a minuta de entendimento de {member_name}.", minute["understanding_pdf"]))
        if not presentation_text:
            issues.append(Issue("E_PDF_TEXT_UNAVAILABLE", f"Não foi possível ler a minuta de apresentação de {member_name}.", minute["presentation_pdf"]))

        _require_text(issues, understanding_text, member_name, minute["understanding_pdf"], "o nome da pessoa")
        for text, key in ((understanding_text, "understanding_pdf"), (presentation_text, "presentation_pdf")):
            header = text[:1400]
            for expected in (
                member_name,
                block["title"],
                f"Dificuldade técnica: {block['difficulty']['score']}/10",
                f"Relevância para a apresentação: {block['relevance']['score']}/10",
            ):
                _require_text(issues, header, expected, minute[key], f"cabeçalho inicial: {expected}")
        for heading in ("Entrada", "Saída", "Glossário"):
            _require_text(issues, understanding_text, heading, minute["understanding_pdf"], heading)
        for unit_id in block["question_unit_ids"]:
            unit = units[unit_id]
            _require_text(issues, understanding_text, question_text(unit), minute["understanding_pdf"], unit_id)
            parent = questions[unit["parent_question_id"]]
            _require_text(
                issues,
                understanding_text,
                question_text(parent),
                minute["understanding_pdf"],
                f"pergunta ou objetivo {unit['parent_question_id']}",
            )
            if parent.get("origin") == "derived":
                _require_text(issues, understanding_text, "Objetivo derivado", minute["understanding_pdf"], "a identificação de objetivo derivado")
            if unit.get("split") is True:
                _require_text(
                    issues,
                    understanding_text,
                    unit.get("scope", ""),
                    minute["understanding_pdf"],
                    f"escopo de {unit_id}",
                )
            _require_text(issues, presentation_text, question_text(unit), minute["presentation_pdf"], unit_id)
        for section_id in block.get("owned_guide_section_ids", []) + block.get("prerequisite_guide_section_ids", []):
            section = sections[section_id]
            if not (_contains(understanding_text, section_id) or _contains(understanding_text, section.get("title", ""))):
                issues.append(Issue("E_MINUTE_CONTENT", f"Minuta de {member_name} não referencia a seção {section_id}.", minute["understanding_pdf"]))
        for term_id in block.get("glossary_term_ids", []):
            term = glossary[term_id]
            if not (_contains(understanding_text, term_id) or _contains(understanding_text, term.get("full_name", ""))):
                issues.append(Issue("E_MINUTE_GLOSSARY", f"Glossário local de {member_name} não contém {term_id}.", minute["understanding_pdf"]))
        _require_text(issues, presentation_text, member_name, minute["presentation_pdf"], "o nome da pessoa")
        _require_text(issues, presentation_text, "Tempo", minute["presentation_pdf"], "o tempo")
        _require_text(issues, presentation_text, "Transição", minute["presentation_pdf"], "a transição")
        for slide_id in block["slide_ids"]:
            slide = slides_by_id[slide_id]
            if not (_contains(presentation_text, slide_id) or _contains(presentation_text, slide["title"])):
                issues.append(Issue("E_MINUTE_CONTENT", f"Minuta de {member_name} não cobre o slide {slide_id}.", minute["presentation_pdf"]))

        _validate_facts(issues, understanding_text, block.get("fact_ids", []), facts, "understanding", minute["understanding_pdf"])
        minute_slide_facts = [fact_id for slide_id in block["slide_ids"] for fact_id in slides_by_id[slide_id].get("fact_ids", [])]
        _validate_facts(issues, presentation_text, minute_slide_facts, facts, "presentation_minute", minute["presentation_pdf"])

    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--package", type=Path)
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args()

    try:
        data = load_manifest(args.manifest)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"E_MANIFEST_READ: {exc}", file=sys.stderr)
        return 1

    issues = validate_package(data, args.package)
    if args.format == "json":
        print(json.dumps({"ok": not issues, "issues": [issue.as_dict() for issue in issues]}, ensure_ascii=False, indent=2))
    elif issues:
        for issue in issues:
            location = f" [{issue.path}]" if issue.path else ""
            print(f"{issue.code}{location}: {issue.message}", file=sys.stderr)
    else:
        print("Pacote válido.")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
