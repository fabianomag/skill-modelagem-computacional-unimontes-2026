#!/usr/bin/env python3
"""Create the public/internal skeleton without overwriting existing content."""

from __future__ import annotations

import argparse
import html
import shutil
import sys
import zipfile
from pathlib import Path

from approve_manifest import atomic_json_write, seal_manifest
from generate_deck_data import write_deck_data
from manifest_lib import load_manifest, question_text, validate_manifest


SKILL_DIR = Path(__file__).resolve().parents[1]


def copy_if_absent(source: Path, destination: Path) -> None:
    if destination.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def personalise_report_template(source: Path, destination: Path, team: list[dict]) -> None:
    """Fill literal name placeholders in DOCX XML, retaining all other ZIP entries."""
    if destination.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    replacements = {
        f"[Integrante {index}]": html.escape(member["name"], quote=False)
        for index, member in enumerate(team, start=1)
    }
    temporary = destination.with_name(f".{destination.name}.tmp")
    try:
        with zipfile.ZipFile(source) as src, zipfile.ZipFile(temporary, "w") as target:
            for info in src.infolist():
                content = src.read(info.filename)
                if info.filename.endswith(".xml"):
                    xml = content.decode("utf-8")
                    for token, name in replacements.items():
                        xml = xml.replace(token, name)
                    content = xml.encode("utf-8")
                target.writestr(info, content)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def write_minute_source(template: Path, destination: Path, data: dict, member: dict, block: dict) -> None:
    if destination.exists():
        return
    units = {unit["id"]: unit for unit in data["problem"]["question_units"]}
    questions = {q["id"]: q for q in data["problem"]["questions"]}
    assigned = [units[unit_id] for unit_id in block["question_unit_ids"]]
    parent_ids = list(dict.fromkeys(unit["parent_question_id"] for unit in assigned))
    question_lines = [
        ("Objetivo derivado: " if questions[qid].get("origin") == "derived" else "Pergunta do enunciado: ")
        + question_text(questions[qid]) for qid in parent_ids
    ]
    replacements = {
        "PESSOA": member["name"],
        "TITULO_DO_BLOCO": block["title"],
        "DIFICULDADE": str(block["difficulty"]["score"]),
        "RELEVANCIA": str(block["relevance"]["score"]),
        "MOTIVO_DIFICULDADE": block["difficulty"]["rationale"],
        "MOTIVO_RELEVANCIA": block["relevance"]["rationale"],
        "SECOES_PROPRIAS": ", ".join(block["owned_guide_section_ids"]),
        "SECOES_COMPARTILHADAS": ", ".join(block["prerequisite_guide_section_ids"]) or "Nenhuma",
        "SLIDES_EXCLUSIVOS": ", ".join(block["slide_ids"]),
        "TEMPO_TOTAL": f"{block['seconds']} segundos",
        "PERGUNTAS_EXATAS": " / ".join(question_lines),
        "PERGUNTAS_OU_OBJETIVOS": " / ".join(question_lines),
        "PERGUNTAS_ORIGINAIS_EXATAS_OU_OBJETIVOS_DERIVADOS_IDENTIFICADOS": "\n\n".join(question_lines),
        "COPIA_EXATA_DAS_PERGUNTAS_ORIGINAIS": "\n\n".join(question_lines),
        "PERGUNTAS_OU_OBJETIVOS_ATRIBUIDOS": "\n\n".join(question_lines),
        "UNIDADE_ATRIBUIDA_E_FRONTEIRA_CONCEITUAL_SE_HOUVER_DIVISAO": "\n\n".join(
            unit.get("scope") or question_text(unit) for unit in assigned
        ),
    }
    content = template.read_text(encoding="utf-8")
    for key, value in replacements.items():
        content = content.replace("{{" + key + "}}", value)
    # Keep the front matter complete even when using an older local template.
    if "Dificuldade técnica:" not in content[:800]:
        title, separator, rest = content.partition("\n")
        content = (title + "\n\n" + f"**Dificuldade técnica:** {block['difficulty']['score']}/10  \n"
                   + f"**Relevância para a apresentação:** {block['relevance']['score']}/10\n" + separator + rest)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")


def safe_target(path: Path, *, kind: str) -> bool:
    resolved = path.resolve()
    forbidden = {Path("/"), Path.home(), Path.home() / "Desktop"}
    if resolved in forbidden or len(resolved.parts) < 3:
        return False
    if kind == "package":
        return resolved.name == "Exercício Grupo"
    if kind == "build":
        return resolved.parent.name == ".modelagem-build"
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()

    data = load_manifest(args.manifest)
    if data.get("review_gate", {}).get("mode", "direct") == "direct":
        issues = seal_manifest(data)
        if not issues:
            atomic_json_write(args.manifest, data)
    else:
        issues = validate_manifest(data)
    if issues:
        for issue in issues:
            print(f"{issue.code}: {issue.message}", file=sys.stderr)
        return 1

    package = Path(data["project"]["package_root"]).expanduser()
    build = Path(data["project"]["build_root"]).expanduser()
    if not safe_target(package, kind="package") or not safe_target(build, kind="build"):
        print("Destino amplo ou inseguro; use pastas específicas do problema.", file=sys.stderr)
        return 1

    public_dirs = [
        package / "Material de Estudo" / "Minutas",
        package / "Entregaveis" / "Relatorio",
        package / "Entregaveis" / "Apresentacao" / "assets",
    ]
    if data["delivery"]["code"]["include"]:
        public_dirs.append(package / "Entregaveis" / "Codigo")
    for directory in public_dirs:
        directory.mkdir(parents=True, exist_ok=True)

    source_root = build / "sources"
    (source_root / "minutas").mkdir(parents=True, exist_ok=True)
    copy_if_absent(SKILL_DIR / "assets" / "guide-source-template.md", source_root / "01-guia-central-do-problema.md")
    personalise_report_template(
        SKILL_DIR / "assets" / "report-template.docx",
        package / data["artifacts"]["report"]["source_docx"],
        data["team"],
    )
    blocks_by_member = {block["member_id"]: block for block in data["blocks"]}
    for member in data["team"]:
        member_id = member["id"]
        block = blocks_by_member[member_id]
        write_minute_source(
            SKILL_DIR / "assets" / "understanding-source-template.md",
            source_root / "minutas" / f"{member_id}-entendimento.md",
            data, member, block,
        )
        write_minute_source(
            SKILL_DIR / "assets" / "presentation-minutes-source-template.md",
            source_root / "minutas" / f"{member_id}-apresentacao.md",
            data, member, block,
        )

    deck_source = SKILL_DIR / "assets" / "presentation-html"
    deck_destination = package / "Entregaveis" / "Apresentacao"
    for source in deck_source.rglob("*"):
        if source.is_file() and source.name != "deck-data.js":
            copy_if_absent(source, deck_destination / source.relative_to(deck_source))
    katex_source = SKILL_DIR / "assets" / "vendor" / "katex"
    katex_destination = deck_destination / "assets" / "vendor" / "katex"
    for source in katex_source.rglob("*"):
        if source.is_file():
            copy_if_absent(source, katex_destination / source.relative_to(katex_source))
    deck_data = deck_destination / "deck-data.js"
    if not deck_data.exists():
        write_deck_data(data, deck_data)

    print(f"Pacote: {package}")
    print(f"Fontes internas: {build}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
