#!/usr/bin/env python3
"""Shared manifest validation for modelagem-computacional-grupo."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


TEAM_SIZE = 5


def question_text(question: dict[str, Any]) -> str:
    """A supplied question is literal; a derived objective is explicitly authored."""
    return question.get("exact_text", question.get("text", ""))


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    path: str = ""

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "path": self.path}


def load_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path)
    with manifest_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("O manifesto deve ser um objeto JSON.")
    return data


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def matrix_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Return only assignment fields controlled by the review gate."""
    problem = data.get("problem") if isinstance(data.get("problem"), dict) else {}
    guide = data.get("guide") if isinstance(data.get("guide"), dict) else {}
    delivery = data.get("delivery") if isinstance(data.get("delivery"), dict) else {}
    raw_blocks = data.get("blocks") if isinstance(data.get("blocks"), list) else []
    raw_slides = data.get("slides") if isinstance(data.get("slides"), list) else []
    raw_sections = guide.get("sections") if isinstance(guide.get("sections"), list) else []
    blocks = []
    for block in raw_blocks:
        if not isinstance(block, dict):
            blocks.append({"invalid": repr(block)})
            continue
        blocks.append(
            {
                key: block.get(key)
                for key in (
                    "id",
                    "order",
                    "member_id",
                    "title",
                    "question_unit_ids",
                    "difficulty",
                    "relevance",
                    "owned_guide_section_ids",
                    "prerequisite_guide_section_ids",
                    "slide_ids",
                    "seconds",
                    "transition_to_block_id",
                    "cohesion_rationale",
                )
            }
        )
    slides = []
    for slide in raw_slides:
        if not isinstance(slide, dict):
            slides.append({"invalid": repr(slide)})
            continue
        slides.append(
            {
                key: slide.get(key)
                for key in (
                    "id",
                    "ordinal",
                    "title",
                    "owner_block_id",
                    "question_unit_ids",
                    "seconds",
                )
            }
        )
    return {
        "team": data.get("team", []),
        "questions": problem.get("questions", []),
        "question_units": problem.get("question_units", []),
        "guide_sections": [
            {"id": section.get("id"), "title": section.get("title")}
            if isinstance(section, dict)
            else {"invalid": repr(section)}
            for section in raw_sections
        ],
        "blocks": blocks,
        "slides": slides,
        "duration": delivery.get("duration", {}),
    }


def matrix_digest(data: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(matrix_payload(data))).hexdigest()


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _duplicates(values: Iterable[str]) -> set[str]:
    counts = Counter(values)
    return {value for value, count in counts.items() if value and count > 1}


def _is_nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_plain_int(value: Any) -> bool:
    return type(value) is int


def _relative_artifact_path(value: Any) -> bool:
    if not _is_nonempty_text(value):
        return False
    if "\\" in value or value.strip() in {".", ".."}:
        return False
    path = Path(value)
    return (
        not path.is_absolute()
        and ".." not in path.parts
        and bool(path.name)
        and bool(path.suffix)
    )


def validate_manifest(data: dict[str, Any], *, allow_pending: bool = False) -> list[Issue]:
    issues: list[Issue] = []

    def error(code: str, message: str, path: str = "") -> None:
        issues.append(Issue(code, message, path))

    def id_list(value: Any, path: str) -> list[str]:
        if not isinstance(value, list):
            error("E_ID_LIST", "O campo deve ser uma lista de IDs.", path)
            return []
        result: list[str] = []
        for index, item in enumerate(value):
            if not _is_nonempty_text(item):
                error("E_ID_LIST", "Cada ID deve ser texto não vazio.", f"{path}[{index}]")
            else:
                result.append(item)
        for duplicate in sorted(_duplicates(result)):
            error("E_ID_LIST", f"ID repetido: {duplicate}.", path)
        return result

    if data.get("schema_version") != 1:
        error("E_SCHEMA_VERSION", "schema_version deve ser 1.", "schema_version")

    project = data.get("project") if isinstance(data.get("project"), dict) else {}
    for key in ("id", "title", "package_root", "build_root"):
        if not _is_nonempty_text(project.get(key)):
            error("E_PROJECT_FIELD", f"project.{key} é obrigatório.", f"project.{key}")
    for key in ("package_root", "build_root"):
        value = project.get(key)
        if _is_nonempty_text(value) and not Path(value).is_absolute():
            error("E_PROJECT_PATH", f"project.{key} deve ser absoluto.", f"project.{key}")
    if _is_nonempty_text(project.get("package_root")) and _is_nonempty_text(project.get("build_root")):
        package_root = Path(project["package_root"]).expanduser().resolve()
        build_root = Path(project["build_root"]).expanduser().resolve()
        if package_root == build_root or package_root in build_root.parents or build_root in package_root.parents:
            error(
                "E_BUILD_PUBLIC_OVERLAP",
                "package_root e build_root devem ser pastas separadas, sem relação de ancestralidade.",
                "project",
            )

    source = data.get("source") if isinstance(data.get("source"), dict) else {}
    if source.get("copy_original_to_package") is not False:
        error(
            "E_SOURCE_COPY_POLICY",
            "O original deve permanecer fora do pacote compartilhável.",
            "source.copy_original_to_package",
        )
    for key in ("original_path", "extracted_markdown_path"):
        if not _is_nonempty_text(source.get(key)):
            error("E_SOURCE_FIELD", f"source.{key} é obrigatório.", f"source.{key}")
        elif not Path(source[key]).expanduser().is_absolute():
            error("E_SOURCE_PATH", f"source.{key} deve ser absoluto.", f"source.{key}")

    team = data.get("team") if isinstance(data.get("team"), list) else []
    team_map: dict[str, str] = {}
    team_names: list[str] = []
    for index, member in enumerate(team):
        if not isinstance(member, dict):
            error("E_TEAM", "Cada integrante deve ser um objeto.", f"team[{index}]")
            continue
        member_id = member.get("id")
        name = member.get("name")
        if not _is_nonempty_text(member_id) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", member_id):
            error("E_TEAM_ID", "ID de integrante deve ser um identificador seguro em minúsculas.", f"team[{index}].id")
        if not _is_nonempty_text(name):
            error("E_TEAM_NAME", "Nome do integrante é obrigatório e vem do pedido do usuário.", f"team[{index}].name")
        if _is_nonempty_text(member_id) and member_id in team_map:
            error("E_TEAM_DUPLICATE", f"Integrante repetido: {member_id}.", f"team[{index}]")
        if _is_nonempty_text(member_id) and _is_nonempty_text(name):
            team_map[member_id] = name
            team_names.append(" ".join(name.split()).casefold())
    if len(team_map) != TEAM_SIZE or len(team) != TEAM_SIZE or len(set(team_names)) != TEAM_SIZE:
        error("E_TEAM_COUNT", "A equipe deve conter exatamente cinco integrantes únicos fornecidos no pedido.", "team")

    problem = data.get("problem") if isinstance(data.get("problem"), dict) else {}
    if not _is_nonempty_text(problem.get("statement_markdown")):
        error("E_PROBLEM_STATEMENT", "A cópia fiel do problema é obrigatória.", "problem.statement_markdown")
    questions = problem.get("questions") if isinstance(problem.get("questions"), list) else []
    question_ids: list[str] = []
    questions_by_id: dict[str, dict[str, Any]] = {}
    for index, question in enumerate(questions):
        if not isinstance(question, dict):
            error("E_QUESTION", "Cada pergunta deve ser um objeto.", f"problem.questions[{index}]")
            continue
        question_id = question.get("id")
        origin = question.get("origin")
        if origin not in {"supplied", "derived"}:
            error("E_QUESTION_ORIGIN", "Pergunta exige origin=supplied ou derived.", f"problem.questions[{index}]")
        elif origin == "supplied" and not _is_nonempty_text(question.get("exact_text")):
            error("E_QUESTION_LITERAL", "Pergunta fornecida exige exact_text fiel ao enunciado.", f"problem.questions[{index}]")
        elif origin == "derived" and (not _is_nonempty_text(question.get("text")) or not _is_nonempty_text(question.get("derivation_rationale")) or "exact_text" in question):
            error("E_QUESTION_DERIVED", "Objetivo derivado exige text e derivation_rationale, sem atribuir exact_text ao professor.", f"problem.questions[{index}]")
        if not _is_nonempty_text(question_id) or not _is_nonempty_text(question_text(question)):
            error("E_QUESTION", "Pergunta ou objetivo exige id e texto.", f"problem.questions[{index}]")
        else:
            question_ids.append(question_id)
            questions_by_id[question_id] = question
    for duplicate in sorted(_duplicates(question_ids)):
        error("E_QUESTION_DUPLICATE", f"Pergunta repetida: {duplicate}.", "problem.questions")
    if not question_ids:
        error("E_QUESTION_EMPTY", "Sem perguntas enumeradas, derive objetivos de resolução e marque origin=derived.", "problem.questions")

    units = problem.get("question_units") if isinstance(problem.get("question_units"), list) else []
    unit_ids: list[str] = []
    units_by_parent: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, unit in enumerate(units):
        if not isinstance(unit, dict):
            error("E_QUESTION_UNIT", "Cada unidade de pergunta deve ser um objeto.", f"problem.question_units[{index}]")
            continue
        unit_id = unit.get("id")
        parent = unit.get("parent_question_id")
        if not _is_nonempty_text(unit_id) or not _is_nonempty_text(question_text(unit)):
            error("E_QUESTION_UNIT", "Unidade exige id e texto de pergunta ou objetivo.", f"problem.question_units[{index}]")
            continue
        unit_ids.append(unit_id)
        if parent not in question_ids:
            error("E_QUESTION_PARENT", f"Unidade {unit_id} aponta para pergunta inexistente.", f"problem.question_units[{index}]")
        else:
            units_by_parent[parent].append(unit)
            parent_question = questions_by_id[parent]
            if parent_question.get("origin") == "supplied" and unit.get("exact_text") != parent_question.get("exact_text"):
                error("E_QUESTION_LITERAL", "Mesmo dividida, a unidade deve manter a pergunta literal; delimite a parte em scope.", f"problem.question_units[{index}]")
            if parent_question.get("origin") == "derived" and ("exact_text" in unit or not _is_nonempty_text(unit.get("text"))):
                error("E_QUESTION_DERIVED", "Unidade de objetivo derivado usa text, não exact_text.", f"problem.question_units[{index}]")
        if unit.get("split") is True and not _is_nonempty_text(unit.get("split_rationale")):
            error("E_SPLIT_RATIONALE", f"Divisão de {unit_id} exige justificativa.", f"problem.question_units[{index}]")
        if unit.get("split") is True and not _is_nonempty_text(unit.get("scope")):
            error(
                "E_SPLIT_SCOPE",
                f"Divisão de {unit_id} exige a fronteira atribuída em scope.",
                f"problem.question_units[{index}]",
            )
    for duplicate in sorted(_duplicates(unit_ids)):
        error("E_QUESTION_UNIT_DUPLICATE", f"Unidade repetida: {duplicate}.", "problem.question_units")
    for question_id in question_ids:
        if not units_by_parent.get(question_id):
            error("E_QUESTION_COVERAGE", f"Pergunta {question_id} não possui unidade atribuível.", "problem.question_units")
        elif len(units_by_parent[question_id]) > 1:
            for unit in units_by_parent[question_id]:
                if (
                    unit.get("split") is not True
                    or not _is_nonempty_text(unit.get("split_rationale"))
                    or not _is_nonempty_text(unit.get("scope"))
                ):
                    error(
                        "E_SPLIT_RATIONALE",
                        f"A pergunta {question_id} foi dividida; todas as unidades exigem split=true, justificativa e scope.",
                        "problem.question_units",
                    )

    guide = data.get("guide") if isinstance(data.get("guide"), dict) else {}
    sections = guide.get("sections") if isinstance(guide.get("sections"), list) else []
    section_ids = []
    for index, section in enumerate(sections):
        if not isinstance(section, dict) or not _is_nonempty_text(section.get("id")) or not _is_nonempty_text(section.get("title")):
            error("E_SECTION", "Cada seção exige id e title.", f"guide.sections[{index}]")
            continue
        section_ids.append(section["id"])
    for duplicate in sorted(_duplicates(section_ids)):
        error("E_SECTION_DUPLICATE", f"Seção repetida: {duplicate}.", "guide.sections")
    glossary = guide.get("glossary_terms") if isinstance(guide.get("glossary_terms"), list) else []
    glossary_id_list: list[str] = []
    for index, term in enumerate(glossary):
        required = ("id", "full_name", "conceptual_meaning", "unit_rule", "purpose")
        if not isinstance(term, dict) or any(not _is_nonempty_text(term.get(key)) for key in required):
            error("E_GLOSSARY_TERM", "Termo do glossário exige id, nome, conceito, unidade e uso.", f"guide.glossary_terms[{index}]")
            continue
        glossary_id_list.append(term["id"])
    for duplicate in sorted(_duplicates(glossary_id_list)):
        error("E_GLOSSARY_DUPLICATE", f"Termo repetido: {duplicate}.", "guide.glossary_terms")
    glossary_ids = set(glossary_id_list)

    facts = data.get("facts") if isinstance(data.get("facts"), list) else []
    fact_id_list: list[str] = []
    for index, fact in enumerate(facts):
        if not isinstance(fact, dict) or not _is_nonempty_text(fact.get("id")) or fact.get("value") is None:
            error("E_FACT", "Fato exige id e valor canônico.", f"facts[{index}]")
            continue
        if not _is_nonempty_text(fact.get("unit")):
            error("E_FACT", f"Fato {fact.get('id')} exige unidade explícita; use 'adimensional' quando couber.", f"facts[{index}].unit")
        if not isinstance(fact.get("formats"), dict):
            error("E_FACT", f"Fato {fact.get('id')} exige formats.", f"facts[{index}].formats")
        provenance = fact.get("provenance")
        if not isinstance(provenance, dict) or not _is_nonempty_text(provenance.get("kind")):
            error("E_FACT", f"Fato {fact.get('id')} exige proveniência.", f"facts[{index}].provenance")
        fact_id_list.append(fact["id"])
    for duplicate in sorted(_duplicates(fact_id_list)):
        error("E_FACT_DUPLICATE", f"Fato repetido: {duplicate}.", "facts")
    fact_ids = set(fact_id_list)

    blocks = data.get("blocks") if isinstance(data.get("blocks"), list) else []
    if len(blocks) != 5:
        error("E_BLOCK_COUNT", "Devem existir exatamente cinco blocos.", "blocks")
    block_ids: list[str] = []
    block_by_id: dict[str, dict[str, Any]] = {}
    member_ids: list[str] = []
    order_values: list[int] = []
    assigned_units: list[str] = []
    owned_sections: list[str] = []
    for index, block in enumerate(blocks):
        path = f"blocks[{index}]"
        if not isinstance(block, dict):
            error("E_BLOCK", "Cada bloco deve ser um objeto.", path)
            continue
        block_id = block.get("id")
        member_id = block.get("member_id")
        if not _is_nonempty_text(block_id):
            error("E_BLOCK_ID", "Bloco exige id.", path)
            continue
        block_ids.append(block_id)
        block_by_id[block_id] = block
        member_ids.append(member_id if _is_nonempty_text(member_id) else repr(member_id))
        if not _is_nonempty_text(member_id) or member_id not in team_map:
            error("E_BLOCK_MEMBER", f"Membro inválido em {block_id}.", f"{path}.member_id")
        order = block.get("order")
        if not _is_plain_int(order):
            error("E_BLOCK_ORDER", f"Ordem inválida em {block_id}.", f"{path}.order")
        else:
            order_values.append(order)
        if not _is_nonempty_text(block.get("title")):
            error("E_BLOCK_TITLE", f"Bloco {block_id} exige título.", f"{path}.title")
        unit_refs = id_list(block.get("question_unit_ids"), f"{path}.question_unit_ids")
        if not unit_refs:
            error("E_BLOCK_QUESTION", f"Bloco {block_id} precisa de ao menos uma unidade de pergunta.", f"{path}.question_unit_ids")
        for unit_id in unit_refs:
            if unit_id not in unit_ids:
                error("E_BLOCK_QUESTION", f"Bloco {block_id} usa unidade inexistente {unit_id}.", f"{path}.question_unit_ids")
            assigned_units.append(unit_id)
        for metric, label in (("difficulty", "Dificuldade"), ("relevance", "Relevância")):
            rating = block.get(metric) if isinstance(block.get(metric), dict) else {}
            score = rating.get("score")
            if not _is_plain_int(score) or not 0 <= score <= 10:
                error(f"E_{metric.upper()}", f"{label} de {block_id} deve ser inteira entre 0 e 10.", f"{path}.{metric}.score")
            if not _is_nonempty_text(rating.get("rationale")):
                error(f"E_{metric.upper()}", f"{label} de {block_id} exige justificativa.", f"{path}.{metric}.rationale")
        if not _is_nonempty_text(block.get("cohesion_rationale")):
            error("E_COHESION", f"Bloco {block_id} exige justificativa de coesão.", f"{path}.cohesion_rationale")
        own = id_list(block.get("owned_guide_section_ids"), f"{path}.owned_guide_section_ids")
        prereq = id_list(block.get("prerequisite_guide_section_ids"), f"{path}.prerequisite_guide_section_ids")
        for section_id in own + prereq:
            if section_id not in section_ids:
                error("E_SECTION_REFERENCE", f"Bloco {block_id} usa seção inexistente {section_id}.", path)
        owned_sections.extend(own)
        for term_id in id_list(block.get("glossary_term_ids"), f"{path}.glossary_term_ids"):
            if term_id not in glossary_ids:
                error("E_GLOSSARY_REFERENCE", f"Bloco {block_id} usa termo inexistente {term_id}.", path)
        for fact_id in id_list(block.get("fact_ids"), f"{path}.fact_ids"):
            if fact_id not in fact_ids:
                error("E_FACT_REFERENCE", f"Bloco {block_id} usa fato inexistente {fact_id}.", path)
        if not _is_plain_int(block.get("seconds")) or block.get("seconds", 0) <= 0:
            error("E_BLOCK_TIME", f"Tempo inválido em {block_id}.", f"{path}.seconds")
    for duplicate in sorted(_duplicates(block_ids)):
        error("E_BLOCK_DUPLICATE", f"Bloco repetido: {duplicate}.", "blocks")
    if set(member_ids) != set(team_map) or len(member_ids) != TEAM_SIZE:
        error("E_MEMBER_ASSIGNMENT", "Cada integrante deve possuir exatamente um bloco.", "blocks")
    if sorted(order_values) != [1, 2, 3, 4, 5]:
        error("E_BLOCK_ORDER", "As ordens dos blocos devem ser 1, 2, 3, 4 e 5.", "blocks")
    for duplicate in sorted(_duplicates(assigned_units)):
        error("E_QUESTION_COVERAGE", f"Unidade atribuída mais de uma vez: {duplicate}.", "blocks")
    missing_units = sorted(set(unit_ids) - set(assigned_units))
    if missing_units:
        error("E_QUESTION_COVERAGE", f"Unidades sem bloco: {', '.join(missing_units)}.", "blocks")
    for duplicate in sorted(_duplicates(owned_sections)):
        error("E_SECTION_OVERLAP", f"Seção própria atribuída mais de uma vez: {duplicate}.", "blocks")

    slides = data.get("slides") if isinstance(data.get("slides"), list) else []
    slide_ids: list[str] = []
    slide_ordinals: list[int] = []
    slides_by_block: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    units_seen_in_slide: defaultdict[str, set[str]] = defaultdict(set)
    for index, slide in enumerate(slides):
        path = f"slides[{index}]"
        if not isinstance(slide, dict):
            error("E_SLIDE", "Cada slide deve ser um objeto.", path)
            continue
        slide_id = slide.get("id")
        owner = slide.get("owner_block_id")
        if not _is_nonempty_text(slide_id):
            error("E_SLIDE_ID", "Slide exige id.", path)
            continue
        slide_ids.append(slide_id)
        ordinal = slide.get("ordinal")
        if _is_plain_int(ordinal):
            slide_ordinals.append(ordinal)
        else:
            error("E_SLIDE_ORDER", f"Slide {slide_id} exige ordinal inteiro.", f"{path}.ordinal")
        if not _is_nonempty_text(owner) or owner not in block_by_id:
            error("E_SLIDE_OWNER", f"Slide {slide_id} aponta para bloco inexistente.", f"{path}.owner_block_id")
        else:
            slides_by_block[owner].append(slide)
        if not _is_nonempty_text(slide.get("title")):
            error("E_SLIDE_TITLE", f"Slide {slide_id} exige título.", f"{path}.title")
        slide_unit_ids = id_list(slide.get("question_unit_ids"), f"{path}.question_unit_ids")
        for unit_id in slide_unit_ids:
            if _is_nonempty_text(owner) and owner in block_by_id and unit_id not in block_by_id[owner].get("question_unit_ids", []):
                error("E_SLIDE_QUESTION", f"Slide {slide_id} usa unidade fora de seu bloco: {unit_id}.", path)
            units_seen_in_slide[owner if _is_nonempty_text(owner) else "__invalid__"].add(unit_id)
        for term_id in id_list(slide.get("glossary_term_ids"), f"{path}.glossary_term_ids"):
            if term_id not in glossary_ids:
                error("E_GLOSSARY_REFERENCE", f"Slide {slide_id} usa termo inexistente {term_id}.", path)
        for fact_id in id_list(slide.get("fact_ids"), f"{path}.fact_ids"):
            if fact_id not in fact_ids:
                error("E_FACT_REFERENCE", f"Slide {slide_id} usa fato inexistente {fact_id}.", path)
        if not _is_plain_int(slide.get("seconds")) or slide.get("seconds", 0) <= 0:
            error("E_SLIDE_TIME", f"Tempo inválido no slide {slide_id}.", f"{path}.seconds")
    for duplicate in sorted(_duplicates(slide_ids)):
        error("E_SLIDE_DUPLICATE", f"Slide repetido: {duplicate}.", "slides")
    if slide_ordinals and sorted(slide_ordinals) != list(range(1, len(slides) + 1)):
        error("E_SLIDE_ORDER", "Os ordinais dos slides devem ser contínuos a partir de 1.", "slides")

    ordered_blocks = sorted(
        (block for block in blocks if isinstance(block, dict) and _is_plain_int(block.get("order"))),
        key=lambda block: block["order"],
    )
    previous_max = 0
    for position, block in enumerate(ordered_blocks):
        block_id = block.get("id")
        owned_slides = slides_by_block.get(block_id, [])
        ordinals = sorted(slide.get("ordinal") for slide in owned_slides if _is_plain_int(slide.get("ordinal")))
        referenced = id_list(block.get("slide_ids"), f"blocks[{block_id}].slide_ids")
        actual_ids = [slide.get("id") for slide in sorted(owned_slides, key=lambda slide: slide.get("ordinal", 0))]
        if referenced != actual_ids:
            error("E_SLIDE_OWNER", f"slide_ids de {block_id} não coincide com os slides cujo owner é o bloco.", "blocks")
        if not ordinals:
            error("E_SLIDE_OWNER", f"Bloco {block_id} não possui slide.", "blocks")
        elif ordinals != list(range(min(ordinals), max(ordinals) + 1)):
            error("E_SLIDE_CONTIGUITY", f"Slides de {block_id} não são contíguos.", "slides")
        elif min(ordinals) <= previous_max:
            error("E_SLIDE_CONTIGUITY", f"Ordem dos apresentadores se sobrepõe em {block_id}.", "slides")
        if ordinals:
            previous_max = max(ordinals)
        block_units = id_list(block.get("question_unit_ids"), f"blocks[{block_id}].question_unit_ids")
        missing_on_slides = set(block_units) - units_seen_in_slide.get(block_id, set())
        if missing_on_slides:
            error("E_SLIDE_QUESTION", f"Unidades de {block_id} sem slide: {', '.join(sorted(missing_on_slides))}.", "slides")
        slide_seconds = sum(slide.get("seconds", 0) for slide in owned_slides if _is_plain_int(slide.get("seconds")))
        if slide_seconds != block.get("seconds"):
            error("E_TIME_SUM", f"Tempo dos slides de {block_id} ({slide_seconds}) difere do bloco ({block.get('seconds')}).", "blocks")
        expected_transition = ordered_blocks[position + 1].get("id") if position + 1 < len(ordered_blocks) else None
        if block.get("transition_to_block_id") != expected_transition:
            error("E_TRANSITION", f"Transição de {block_id} deve apontar para {expected_transition}.", "blocks")

    delivery = data.get("delivery") if isinstance(data.get("delivery"), dict) else {}
    duration = delivery.get("duration") if isinstance(delivery.get("duration"), dict) else {}
    max_seconds = duration.get("max_seconds")
    if not _is_plain_int(max_seconds) or max_seconds <= 0:
        error("E_DURATION", "A duração máxima deve ser um inteiro positivo.", "delivery.duration.max_seconds")
    elif sum(slide.get("seconds", 0) for slide in slides if isinstance(slide, dict) and _is_plain_int(slide.get("seconds"))) > max_seconds:
        error("E_DURATION", "A apresentação excede a duração máxima.", "delivery.duration")
    if duration.get("source") not in {"official", "assumed"}:
        error("E_DURATION_SOURCE", "A fonte da duração deve ser official ou assumed.", "delivery.duration.source")
    if duration.get("source") == "assumed" and max_seconds != 600:
        error("E_DURATION_DEFAULT", "Sem duração oficial, o padrão é 600 segundos.", "delivery.duration")
    code = delivery.get("code") if isinstance(delivery.get("code"), dict) else {}
    rubric = code.get("rubric")
    reproducibility = code.get("reproducibility")
    if rubric not in {"required", "not_stated", "forbidden"}:
        error("E_CODE_POLICY", "rubric deve ser required, not_stated ou forbidden.", "delivery.code.rubric")
    if reproducibility not in {"required", "not_required"}:
        error("E_CODE_POLICY", "reproducibility deve ser required ou not_required.", "delivery.code.reproducibility")
    should_include_code = rubric == "required" or reproducibility == "required"
    if rubric == "forbidden" and reproducibility == "required":
        error("E_CODE_POLICY", "Rubrica proíbe código, mas a reprodutibilidade foi marcada como obrigatória.", "delivery.code")
    if code.get("include") is not should_include_code:
        error("E_CODE_POLICY", f"delivery.code.include deve ser {str(should_include_code).lower()}.", "delivery.code.include")
    dependencies = code.get("external_dependencies")
    if not isinstance(dependencies, list) or any(not _is_nonempty_text(item) for item in dependencies):
        error("E_CODE_POLICY", "external_dependencies deve ser uma lista de nomes não vazios.", "delivery.code.external_dependencies")

    artifacts = data.get("artifacts") if isinstance(data.get("artifacts"), dict) else {}
    report_artifacts = artifacts.get("report") if isinstance(artifacts.get("report"), dict) else {}
    presentation_artifacts = artifacts.get("presentation") if isinstance(artifacts.get("presentation"), dict) else {}
    study_artifacts = artifacts.get("study_guide") if isinstance(artifacts.get("study_guide"), dict) else {}
    required_paths = [
        ("report.source_docx", report_artifacts.get("source_docx")),
        ("report.pdf", report_artifacts.get("pdf")),
        ("presentation.html_entry", presentation_artifacts.get("html_entry")),
        ("presentation.pdf", presentation_artifacts.get("pdf")),
        ("study_guide.pdf", study_artifacts.get("pdf")),
    ]
    for label, value in required_paths:
        if not _relative_artifact_path(value):
            error("E_ARTIFACT_PATH", f"Caminho inválido em {label}.", f"artifacts.{label}")
    source_bundle = id_list(presentation_artifacts.get("source_bundle"), "artifacts.presentation.source_bundle")
    for value in source_bundle:
        if not _relative_artifact_path(value):
            error("E_ARTIFACT_PATH", f"Caminho inválido no bundle: {value}.", "artifacts.presentation.source_bundle")
    for fact_id in id_list(report_artifacts.get("required_fact_ids"), "artifacts.report.required_fact_ids"):
        if fact_id not in fact_ids:
            error("E_FACT_REFERENCE", f"Relatório exige fato inexistente {fact_id}.", "artifacts.report.required_fact_ids")
    minutes = artifacts.get("minutes") if isinstance(artifacts.get("minutes"), list) else []
    minute_members: list[str] = []
    for index, minute in enumerate(minutes):
        if not isinstance(minute, dict):
            error("E_MINUTE", "Cada entrada de minuta deve ser um objeto.", f"artifacts.minutes[{index}]")
            continue
        member_id = minute.get("member_id")
        minute_members.append(member_id if _is_nonempty_text(member_id) else repr(member_id))
        if not _is_nonempty_text(member_id) or member_id not in team_map:
            error("E_MINUTE", "Integrante inválido na minuta.", f"artifacts.minutes[{index}].member_id")
        for key in ("understanding_pdf", "presentation_pdf"):
            if not _relative_artifact_path(minute.get(key)):
                error("E_MINUTE", f"Caminho inválido de minuta: {key}.", f"artifacts.minutes[{index}].{key}")
    if set(minute_members) != set(team_map) or len(minute_members) != TEAM_SIZE:
        error("E_MINUTE_COUNT", "Devem existir duas minutas para cada integrante.", "artifacts.minutes")

    gate = data.get("review_gate") if isinstance(data.get("review_gate"), dict) else {}
    if gate.get("mode", "direct") not in {"direct", "review"}:
        error("E_REVIEW_MODE", "O modo deve ser direct (padrão) ou review quando solicitado.", "review_gate.mode")
    status = gate.get("status")
    if status not in {"pending", "approved", "auto_approved"}:
        error("E_REVIEW_GATE", "Status do gate inválido.", "review_gate.status")
    elif status == "pending" and not allow_pending:
        error("E_REVIEW_GATE", "A matriz ainda não foi selada; execução direta usa approve_manifest.py sem pausa humana.", "review_gate.status")
    elif status in {"approved", "auto_approved"}:
        actual_digest = matrix_digest(data)
        if gate.get("matrix_sha256") != actual_digest:
            error("E_REVIEW_HASH", "A matriz mudou depois do selo; valide e sele novamente.", "review_gate.matrix_sha256")

    return issues


def format_matrix_markdown(data: dict[str, Any]) -> str:
    parents = {
        question.get("id"): question
        for question in data.get("problem", {}).get("questions", [])
        if isinstance(question, dict)
    }
    questions = {
        unit.get("id"): (
            ("Objetivo derivado: " if parents.get(unit.get("parent_question_id"), {}).get("origin") == "derived" else "")
            + question_text(unit) + (f" — Escopo: {unit['scope']}" if unit.get("scope") else "")
        )
        for unit in data.get("problem", {}).get("question_units", [])
        if isinstance(unit, dict)
    }
    sections = {
        section.get("id"): section.get("title", section.get("id", ""))
        for section in data.get("guide", {}).get("sections", [])
        if isinstance(section, dict)
    }
    slides = {
        slide.get("id"): slide
        for slide in data.get("slides", [])
        if isinstance(slide, dict)
    }
    team = {member.get("id"): member.get("name") for member in data.get("team", []) if isinstance(member, dict)}
    lines = [
        "| Bloco | Perguntas ou objetivos e escopo | Conteúdo técnico | Dificuldade | Relevância | Pessoa | Seções | Slides | Tempo |",
        "|---|---|---|---:|---:|---|---|---|---:|",
    ]
    for block in sorted(data.get("blocks", []), key=lambda item: item.get("order", 0)):
        question_text = "<br>".join(questions.get(unit_id, unit_id) for unit_id in block.get("question_unit_ids", []))
        difficulty = block.get("difficulty", {}).get("score", "")
        relevance = block.get("relevance", {}).get("score", "")
        own = ", ".join(
            f"{section_id} — {sections.get(section_id, section_id)}"
            for section_id in block.get("owned_guide_section_ids", [])
        )
        slide_text = ", ".join(
            f"{slide_id} — {slides.get(slide_id, {}).get('title', slide_id)}"
            for slide_id in block.get("slide_ids", [])
        )
        lines.append(
            "| {block} | {questions} | {title} | {difficulty}/10 | {relevance}/10 | {member} | {sections} | {slides} | {seconds}s |".format(
                block=block.get("id", ""),
                questions=question_text.replace("|", "\\|"),
                title=str(block.get("title", "")).replace("|", "\\|"),
                difficulty=difficulty,
                relevance=relevance,
                member=team.get(block.get("member_id"), block.get("member_id", "")),
                sections=own.replace("|", "\\|"),
                slides=slide_text.replace("|", "\\|"),
                seconds=block.get("seconds", ""),
            )
        )
    return "\n".join(lines)
