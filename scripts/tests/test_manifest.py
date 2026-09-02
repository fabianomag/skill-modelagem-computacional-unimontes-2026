#!/usr/bin/env python3
"""Deterministic tests for the group-modeling manifest and package validator."""

from __future__ import annotations

import copy
import html
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
import zipfile


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from manifest_lib import file_sha256, matrix_digest, question_text, validate_manifest  # noqa: E402
from validate_package import compute_bundle_sha256, parse_deck_data, validate_package  # noqa: E402


TEST_TEAM = {
    "pessoa1": "Pessoa Um",
    "pessoa2": "Pessoa Dois",
    "pessoa3": "Pessoa Três",
    "pessoa4": "Pessoa Quatro",
    "pessoa5": "Pessoa Cinco",
}


def issue_codes(issues) -> set[str]:
    return {issue.code for issue in issues}


def make_manifest(question_count: int, root: Path) -> dict:
    if question_count < 0:
        raise ValueError("question_count must not be negative")

    derive_objectives = question_count == 0
    question_count = question_count or 5
    questions = [
        ({"id": f"Q{index}", "origin": "derived", "text": f"Objetivo de resolução {index}",
          "derivation_rationale": "Etapa necessária para resolver o problema sem perguntas enumeradas."}
         if derive_objectives else
         {"id": f"Q{index}", "origin": "supplied", "exact_text": f"Pergunta original {index}"})
        for index in range(1, question_count + 1)
    ]

    if question_count < 5:
        parent_indexes = [((index * question_count) // 5) + 1 for index in range(5)]
        parent_counts = {parent: parent_indexes.count(parent) for parent in set(parent_indexes)}
        seen: dict[int, int] = {}
        units = []
        for parent in parent_indexes:
            seen[parent] = seen.get(parent, 0) + 1
            split = parent_counts[parent] > 1
            suffix = chr(96 + seen[parent]) if split else ""
            units.append(
                {
                    "id": f"Q{parent}{suffix}",
                    "parent_question_id": f"Q{parent}",
                    "exact_text": f"Pergunta original {parent}",
                    "split": split,
                    **(
                        {
                            "split_rationale": "Fronteira conceitual verificável.",
                            "scope": f"Escopo conceitual {seen[parent]} da pergunta {parent}",
                        }
                        if split
                        else {}
                    ),
                }
            )
    else:
        units = [
            {
                "id": f"Q{index}",
                "parent_question_id": f"Q{index}",
                **({"text": f"Objetivo de resolução {index}"} if derive_objectives else
                   {"exact_text": f"Pergunta original {index}"}),
                "split": False,
            }
            for index in range(1, question_count + 1)
        ]

    chunks: list[list[dict]] = [[] for _ in range(5)]
    if len(units) == 5:
        for index, unit in enumerate(units):
            chunks[index].append(unit)
    else:
        # Consecutive grouping preserves the natural presentation order.
        quotient, remainder = divmod(len(units), 5)
        cursor = 0
        for index in range(5):
            size = quotient + (1 if index < remainder else 0)
            chunks[index].extend(units[cursor : cursor + size])
            cursor += size

    members = list(TEST_TEAM.items())
    blocks = []
    slides = []
    for index, ((member_id, _), chunk) in enumerate(zip(members, chunks), start=1):
        block_id = f"B{index}"
        slide_id = f"S{index:02d}"
        blocks.append(
            {
                "id": block_id,
                "order": index,
                "member_id": member_id,
                "title": f"Bloco {index}",
                "question_unit_ids": [unit["id"] for unit in chunk],
                "difficulty": {"score": index, "rationale": "Classificação para teste."},
                "relevance": {"score": 6, "rationale": "Contribuição da parte para a explicação completa."},
                "owned_guide_section_ids": [f"G{index:02d}"],
                "prerequisite_guide_section_ids": ["G00"],
                "slide_ids": [slide_id],
                "glossary_term_ids": ["T"],
                "fact_ids": ["metric.test"] if index == 1 else [],
                "seconds": 60,
                "transition_to_block_id": f"B{index + 1}" if index < 5 else None,
                "cohesion_rationale": "Conteúdo autossuficiente para teste.",
            }
        )
        slides.append(
            {
                "id": slide_id,
                "ordinal": index,
                "title": f"Título do slide {index}",
                "owner_block_id": block_id,
                "question_unit_ids": [unit["id"] for unit in chunk],
                "fact_ids": ["metric.test"] if index == 1 else [],
                "glossary_term_ids": ["T"],
                "seconds": 60,
            }
        )

    package = root / "Exercício Grupo"
    build = root / ".modelagem-build" / "case"
    original = root / "enunciado.pdf"
    extracted = build / "enunciado.md"
    manifest = {
        "schema_version": 1,
        "project": {
            "id": "case",
            "title": "Problema de teste",
            "package_root": str(package),
            "build_root": str(build),
        },
        "source": {
            "original_path": str(original),
            "original_sha256": "",
            "extracted_markdown_path": str(extracted),
            "copy_original_to_package": False,
        },
        "team": [{"id": member_id, "name": name} for member_id, name in members],
        "problem": {
            "statement_markdown": "Problema completo de teste.",
            "inputs": [{"id": "T", "meaning": "Entrada", "unit": "u"}],
            "outputs": [{"id": "V", "meaning": "Saída", "unit": "u"}],
            "domain": "Faixa de teste",
            "questions": questions,
            "question_units": units,
        },
        "review_gate": {"mode": "direct", "status": "auto_approved", "matrix_sha256": None, "approved_at": "2026-08-29"},
        "guide": {
            "sections": [
                {"id": "G00", "title": "Problema, dados e foco", "kind": "reprise"},
                *[
                    {"id": f"G{index:02d}", "title": f"Seção {index}", "kind": "concept"}
                    for index in range(1, 6)
                ],
            ],
            "glossary_terms": [
                {
                    "id": "T",
                    "full_name": "Variável de entrada",
                    "conceptual_meaning": "Valor fornecido ao modelo",
                    "unit_rule": "u",
                    "purpose": "Gerar a previsão",
                }
            ],
        },
        "facts": [
            {
                "id": "metric.test",
                "value": "1.000",
                "unit": "u",
                "formats": {
                    "report": "1,000 u",
                    "guide": "1,00 u",
                    "slide": "1,0 u",
                },
                "provenance": {"kind": "computed", "calculation_id": "test-v1"},
            }
        ],
        "blocks": blocks,
        "slides": slides,
        "delivery": {
            "duration": {"max_seconds": 600, "source": "assumed"},
            "code": {
                "rubric": "not_stated",
                "reproducibility": "not_required",
                "include": False,
                "evidence": "Código não exigido no fixture.",
                "external_dependencies": [],
            },
            "zip": {"requested": False},
            "presentation_pdf": True,
        },
        "artifacts": {
            "report": {
                "source_docx": "Entregaveis/Relatorio/relatorio-editavel.docx",
                "pdf": "Entregaveis/Relatorio/relatorio-final.pdf",
                "required_fact_ids": ["metric.test"],
            },
            "presentation": {
                "html_entry": "Entregaveis/Apresentacao/index.html",
                "pdf": "Entregaveis/Apresentacao/apresentacao.pdf",
                "source_bundle": [
                    "Entregaveis/Apresentacao/index.html",
                    "Entregaveis/Apresentacao/styles.css",
                    "Entregaveis/Apresentacao/deck.js",
                    "Entregaveis/Apresentacao/deck-data.js",
                    "Entregaveis/Apresentacao/presenter.html",
                ],
            },
            "study_guide": {"pdf": "Material de Estudo/01-guia-central-do-problema.pdf"},
            "minutes": [
                {
                    "member_id": member_id,
                    "understanding_pdf": f"Material de Estudo/Minutas/{member_id}-entendimento.pdf",
                    "presentation_pdf": f"Material de Estudo/Minutas/{member_id}-apresentacao.pdf",
                }
                for member_id, _ in members
            ],
        },
        "provenance": {
            "report_source_sha256_at_pdf_generation": None,
            "presentation_bundle_sha256_at_pdf_generation": None,
            "generated_pdf_sha256": {},
        },
    }
    manifest["review_gate"]["matrix_sha256"] = matrix_digest(manifest)
    return manifest


def write_docx(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    escaped = html.escape(text)
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{escaped}</w:t></w:r></w:p></w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", document)


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_fake_pdf(path: Path, pages: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    chunks = [b"%PDF-1.4\n"]
    for index, text in enumerate(pages, start=1):
        chunks.append(
            (
                f"{index} 0 obj\n<< /Type /Page >>\nstream\nBT ({_pdf_escape(text)}) Tj ET\n"
                "endstream\nendobj\n"
            ).encode("utf-8")
        )
    chunks.append(b"%%EOF\n")
    path.write_bytes(b"".join(chunks))


def materialise_package(manifest: dict) -> Path:
    package = Path(manifest["project"]["package_root"])
    package.mkdir(parents=True, exist_ok=True)
    original = Path(manifest["source"]["original_path"])
    original.write_bytes(b"original-source")
    manifest["source"]["original_sha256"] = file_sha256(original)

    report = manifest["artifacts"]["report"]
    report_docx = package / report["source_docx"]
    write_docx(report_docx, "Relatório final 1,000 u")
    write_fake_pdf(package / report["pdf"], ["Relatório final 1,000 u"])

    presentation = manifest["artifacts"]["presentation"]
    deck_root = package / "Entregaveis" / "Apresentacao"
    deck_root.mkdir(parents=True, exist_ok=True)
    sections = []
    records = []
    block_by_id = {block["id"]: block for block in manifest["blocks"]}
    people = {member["id"]: member["name"] for member in manifest["team"]}
    for slide in sorted(manifest["slides"], key=lambda item: item["ordinal"]):
        fact = "<p>1,0 u</p>" if slide.get("fact_ids") else ""
        sections.append(
            f'<section class="slide" data-slide-id="{slide["id"]}" '
            f'data-owner-block-id="{slide["owner_block_id"]}"><h2>{slide["title"]}</h2>{fact}</section>'
        )
        member_id = block_by_id[slide["owner_block_id"]]["member_id"]
        records.append(
            "{ id: \"%s\", ownerBlockId: \"%s\", ownerName: \"%s\", title: \"%s\", seconds: %d, notes: \"\", sources: [] }"
            % (slide["id"], slide["owner_block_id"], people[member_id], slide["title"], slide["seconds"])
        )
    (deck_root / "index.html").write_text(
        "<!doctype html><html><head><link rel=\"stylesheet\" href=\"styles.css\"></head><body>"
        + "".join(sections)
        + '<script src="deck-data.js"></script><script src="deck.js"></script></body></html>',
        encoding="utf-8",
    )
    (deck_root / "deck-data.js").write_text(
        "window.MODELAGEM_DECK = { slides: [\n" + ",\n".join(records) + "\n] };\n",
        encoding="utf-8",
    )
    (deck_root / "styles.css").write_text(".slide { width: 100%; }\n", encoding="utf-8")
    (deck_root / "deck.js").write_text("window.DeckAPI = {};\n", encoding="utf-8")
    (deck_root / "presenter.html").write_text("<!doctype html><title>Apresentador</title>", encoding="utf-8")
    write_fake_pdf(
        package / presentation["pdf"],
        [f"{slide['title']} {'1,0 u' if slide.get('fact_ids') else ''}" for slide in manifest["slides"]],
    )

    guide_text = "Entrada Saída Perguntas Glossário 1,00 u " + " ".join(
        ("Objetivo derivado: " if question["origin"] == "derived" else "") + question_text(question)
        for question in manifest["problem"]["questions"]
    )
    write_fake_pdf(package / manifest["artifacts"]["study_guide"]["pdf"], [guide_text])

    units = {unit["id"]: unit for unit in manifest["problem"]["question_units"]}
    for minute in manifest["artifacts"]["minutes"]:
        member_id = minute["member_id"]
        block = next(item for item in manifest["blocks"] if item["member_id"] == member_id)
        assigned_units = [units[unit_id] for unit_id in block["question_unit_ids"]]
        questions = " ".join(question_text(unit) for unit in assigned_units)
        parent_questions = " ".join(
            next(
                ("Objetivo derivado: " if question["origin"] == "derived" else "") + question_text(question)
                for question in manifest["problem"]["questions"]
                if question["id"] == unit["parent_question_id"]
            )
            for unit in assigned_units
        )
        scopes = " ".join(unit.get("scope", "") for unit in assigned_units)
        sections_text = " ".join(block["owned_guide_section_ids"] + block["prerequisite_guide_section_ids"])
        understanding_fact = "1,00 u" if block.get("fact_ids") else ""
        header = (f"{people[member_id]} {block['title']} "
                  f"Dificuldade técnica: {block['difficulty']['score']}/10 "
                  f"Relevância para a apresentação: {block['relevance']['score']}/10 ")
        understanding = (
            f"{header} Reprise do problema Entrada Saída "
            f"{parent_questions} {questions} {scopes} "
            f"{sections_text} Glossário T Variável de entrada {understanding_fact}"
        )
        slide_text = " ".join(
            f"{slide_id} {next(slide['title'] for slide in manifest['slides'] if slide['id'] == slide_id)}"
            for slide_id in block["slide_ids"]
        )
        presentation_fact = "1,0 u" if block.get("fact_ids") else ""
        presentation_text = (
            f"{header} Tempo {questions} {slide_text} {presentation_fact} Transição"
        )
        write_fake_pdf(package / minute["understanding_pdf"], [understanding])
        write_fake_pdf(package / minute["presentation_pdf"], [presentation_text])

    manifest["provenance"]["report_source_sha256_at_pdf_generation"] = file_sha256(report_docx)
    manifest["provenance"]["presentation_bundle_sha256_at_pdf_generation"] = compute_bundle_sha256(
        package, presentation["source_bundle"]
    )
    return package


class ManifestCardinalityTests(unittest.TestCase):
    def _assert_valid(self, question_count: int) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = make_manifest(question_count, Path(temporary))
            self.assertEqual([], validate_manifest(manifest), f"question_count={question_count}")

    def test_fewer_than_five_questions_can_be_split_into_five_blocks(self) -> None:
        self._assert_valid(3)

    def test_no_enumerated_questions_uses_marked_derived_objectives(self) -> None:
        self._assert_valid(0)

    def test_exactly_five_questions_map_one_to_one(self) -> None:
        self._assert_valid(5)

    def test_more_than_five_questions_can_be_grouped(self) -> None:
        self._assert_valid(8)

    def test_missing_or_duplicate_question_unit_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = make_manifest(5, Path(temporary))
            manifest["blocks"][1]["question_unit_ids"] = [manifest["blocks"][0]["question_unit_ids"][0]]
            manifest["review_gate"]["matrix_sha256"] = matrix_digest(manifest)
            self.assertIn("E_QUESTION_COVERAGE", issue_codes(validate_manifest(manifest)))

    def test_split_without_rationale_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = make_manifest(3, Path(temporary))
            manifest["problem"]["question_units"][0].pop("split_rationale", None)
            manifest["review_gate"]["matrix_sha256"] = matrix_digest(manifest)
            self.assertIn("E_SPLIT_RATIONALE", issue_codes(validate_manifest(manifest)))

    def test_split_without_scope_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = make_manifest(3, Path(temporary))
            manifest["problem"]["question_units"][0].pop("scope", None)
            manifest["review_gate"]["matrix_sha256"] = matrix_digest(manifest)
            self.assertIn("E_SPLIT_SCOPE", issue_codes(validate_manifest(manifest)))

    def test_owned_section_overlap_fails_but_shared_prerequisite_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = make_manifest(5, Path(temporary))
            self.assertEqual([], validate_manifest(manifest))
            manifest["blocks"][1]["owned_guide_section_ids"] = manifest["blocks"][0]["owned_guide_section_ids"][:]
            manifest["review_gate"]["matrix_sha256"] = matrix_digest(manifest)
            self.assertIn("E_SECTION_OVERLAP", issue_codes(validate_manifest(manifest)))

    def test_slide_owner_and_contiguity_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = make_manifest(5, Path(temporary))
            manifest["slides"][1]["owner_block_id"] = "B1"
            manifest["review_gate"]["matrix_sha256"] = matrix_digest(manifest)
            codes = issue_codes(validate_manifest(manifest))
            self.assertIn("E_SLIDE_OWNER", codes)

    def test_approved_matrix_hash_detects_assignment_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = make_manifest(5, Path(temporary))
            manifest["blocks"][0]["title"] = "Título alterado depois da aprovação"
            self.assertIn("E_REVIEW_HASH", issue_codes(validate_manifest(manifest)))


class ManifestRobustnessTests(unittest.TestCase):
    def test_arbitrary_team_is_valid_but_duplicate_names_are_not(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = make_manifest(5, Path(temporary))
            for index, member in enumerate(manifest["team"], start=1):
                member["name"] = f"Participante Externo {index}"
            manifest["review_gate"]["matrix_sha256"] = matrix_digest(manifest)
            self.assertEqual([], validate_manifest(manifest))
            manifest["team"][1]["name"] = manifest["team"][0]["name"]
            manifest["review_gate"]["matrix_sha256"] = matrix_digest(manifest)
            self.assertIn("E_TEAM_COUNT", issue_codes(validate_manifest(manifest)))

    def test_relevance_is_required_bounded_and_in_matrix_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = make_manifest(5, Path(temporary))
            manifest["blocks"][0]["relevance"]["score"] = 11
            codes = issue_codes(validate_manifest(manifest))
            self.assertIn("E_RELEVANCE", codes)
            self.assertIn("E_REVIEW_HASH", codes)
            manifest["blocks"][0]["relevance"]["score"] = True
            self.assertIn("E_RELEVANCE", issue_codes(validate_manifest(manifest)))

    def test_derived_objective_must_not_claim_to_be_literal_question(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = make_manifest(0, Path(temporary))
            manifest["problem"]["questions"][0]["exact_text"] = "Texto falsamente atribuído"
            self.assertIn("E_QUESTION_DERIVED", issue_codes(validate_manifest(manifest)))

    def test_split_preserves_literal_question_and_uses_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = make_manifest(3, Path(temporary))
            manifest["problem"]["question_units"][0]["exact_text"] = "Paráfrase indevida"
            self.assertIn("E_QUESTION_LITERAL", issue_codes(validate_manifest(manifest)))

    def test_build_root_cannot_live_inside_public_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = make_manifest(5, Path(temporary))
            manifest["project"]["build_root"] = str(Path(manifest["project"]["package_root"]) / ".modelagem-build" / "case")
            manifest["review_gate"]["matrix_sha256"] = matrix_digest(manifest)
            self.assertIn("E_BUILD_PUBLIC_OVERLAP", issue_codes(validate_manifest(manifest)))

    def test_boolean_is_not_an_integer_for_scores_orders_or_time(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = make_manifest(5, Path(temporary))
            manifest["blocks"][0]["difficulty"]["score"] = True
            manifest["slides"][0]["seconds"] = True
            manifest["review_gate"]["matrix_sha256"] = matrix_digest(manifest)
            codes = issue_codes(validate_manifest(manifest))
            self.assertIn("E_DIFFICULTY", codes)
            self.assertIn("E_SLIDE_TIME", codes)

    def test_multiple_units_require_explicit_split_on_every_unit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = make_manifest(3, Path(temporary))
            manifest["problem"]["question_units"][0]["split"] = False
            manifest["review_gate"]["matrix_sha256"] = matrix_digest(manifest)
            self.assertIn("E_SPLIT_RATIONALE", issue_codes(validate_manifest(manifest)))

    def test_guide_title_change_invalidates_matrix_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = make_manifest(5, Path(temporary))
            manifest["guide"]["sections"][1]["title"] = "Título alterado"
            self.assertIn("E_REVIEW_HASH", issue_codes(validate_manifest(manifest)))

    def test_malformed_artifact_objects_return_issues_instead_of_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = make_manifest(5, Path(temporary))
            manifest["artifacts"]["report"] = []
            manifest["review_gate"]["matrix_sha256"] = matrix_digest(manifest)
            self.assertIn("E_ARTIFACT_PATH", issue_codes(validate_manifest(manifest)))

    def test_fact_and_glossary_ids_must_be_unique_and_report_refs_must_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = make_manifest(5, Path(temporary))
            manifest["facts"].append(copy.deepcopy(manifest["facts"][0]))
            manifest["guide"]["glossary_terms"].append(copy.deepcopy(manifest["guide"]["glossary_terms"][0]))
            manifest["artifacts"]["report"]["required_fact_ids"] = ["missing.fact"]
            manifest["review_gate"]["matrix_sha256"] = matrix_digest(manifest)
            codes = issue_codes(validate_manifest(manifest))
            self.assertTrue({"E_FACT_DUPLICATE", "E_GLOSSARY_DUPLICATE", "E_FACT_REFERENCE"}.issubset(codes))

    def test_generated_json_deck_data_is_parseable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "deck-data.js"
            payload = {
                "slides": [
                    {"id": "S01", "ownerBlockId": "B1", "ownerName": "Pessoa Um", "title": "Abertura", "seconds": 30}
                ]
            }
            path.write_text("window.MODELAGEM_DECK = " + json.dumps(payload, ensure_ascii=False) + ";\n", encoding="utf-8")
            self.assertEqual("Abertura", parse_deck_data(path)[0]["title"])


class DirectProductionTests(unittest.TestCase):
    def test_default_seal_and_scaffold_need_no_human_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = make_manifest(3, root)
            manifest["review_gate"].update(status="pending", matrix_sha256=None)
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = subprocess.run([sys.executable, str(SCRIPTS_DIR / "approve_manifest.py"), str(manifest_path)], capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            sealed = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual("auto_approved", sealed["review_gate"]["status"])
            self.assertEqual([], validate_manifest(sealed))
            # Scaffold also handles a fresh direct-mode assignment without a manual approval call.
            sealed["review_gate"].update(status="pending", matrix_sha256=None)
            manifest_path.write_text(json.dumps(sealed), encoding="utf-8")
            result = subprocess.run([sys.executable, str(SCRIPTS_DIR / "scaffold_case.py"), str(manifest_path)], capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            build = Path(manifest["project"]["build_root"]) / "sources" / "minutas"
            self.assertEqual(10, len(list(build.glob("*.md"))))
            for member in manifest["team"]:
                for kind in ("entendimento", "apresentacao"):
                    text = (build / f"{member['id']}-{kind}.md").read_text(encoding="utf-8")
                    self.assertIn(member["name"], text[:800])
                    self.assertIn("**Relevância para a apresentação:** 6/10", text[:800])
                    self.assertNotIn("{{MOTIVO_DIFICULDADE}}", text)
                    self.assertNotIn("{{MOTIVO_RELEVANCIA}}", text)
                    self.assertNotIn("{{PERGUNTAS_ORIGINAIS_EXATAS_OU_OBJETIVOS_DERIVADOS_IDENTIFICADOS}}", text)
                    self.assertNotIn("{{PERGUNTAS_OU_OBJETIVOS}}", text)
                    self.assertIn("Pergunta do enunciado:", text)
                    self.assertIn("Classificação para teste.", text[:800])
            reloaded = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual("auto_approved", reloaded["review_gate"]["status"])

    def test_explicit_review_mode_retains_optional_pause(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = make_manifest(5, Path(temporary))
            manifest["review_gate"].update(mode="review", status="pending", matrix_sha256=None)
            self.assertEqual([], validate_manifest(manifest, allow_pending=True))
            self.assertIn("E_REVIEW_GATE", issue_codes(validate_manifest(manifest)))

    def test_docx_template_personalisation_uses_prompt_names_and_preserves_source(self) -> None:
        from scaffold_case import personalise_report_template
        from validate_package import extract_docx_text
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, destination = root / "template.docx", root / "report.docx"
            write_docx(source, " | ".join(f"[Integrante {index}]" for index in range(1, 6)))
            original_hash = file_sha256(source)
            team = [{"id": f"p{i}", "name": f"Pessoa {i} & Equipe"} for i in range(1, 6)]
            personalise_report_template(source, destination, team)
            text = extract_docx_text(destination)
            self.assertEqual(original_hash, file_sha256(source))
            self.assertNotIn("[Integrante", text)
            for member in team:
                self.assertIn(member["name"], text)


class PackageValidationTests(unittest.TestCase):
    def test_complete_package_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = make_manifest(5, Path(temporary))
            package = materialise_package(manifest)
            self.assertEqual([], validate_package(manifest, package))

    def test_derived_objectives_package_passes_without_fake_original_questions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = make_manifest(0, Path(temporary))
            package = materialise_package(manifest)
            self.assertEqual([], validate_package(manifest, package))

    def test_minute_header_requires_person_topic_and_both_ratings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = make_manifest(5, Path(temporary))
            package = materialise_package(manifest)
            minute = manifest["artifacts"]["minutes"][0]
            path = package / minute["presentation_pdf"]
            from validate_package import extract_pdf_text
            content = extract_pdf_text(path).replace("Relevância para a apresentação: 6/10", "")
            write_fake_pdf(path, [content])
            self.assertIn("E_MINUTE_CONTENT", issue_codes(validate_package(manifest, package)))

    def test_public_policy_rejects_markdown_zip_code_and_original_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = make_manifest(5, Path(temporary))
            package = materialise_package(manifest)
            (package / "Material de Estudo" / "rascunho.md").write_text("rascunho", encoding="utf-8")
            (package / "pacote.zip").write_bytes(b"zip")
            code = package / "Entregaveis" / "Codigo"
            code.mkdir(parents=True)
            (code / "codigo.py").write_text("print('x')\n", encoding="utf-8")
            (package / "copia-do-original.pdf").write_bytes(Path(manifest["source"]["original_path"]).read_bytes())
            codes = issue_codes(validate_package(manifest, package))
            self.assertTrue({"E_PUBLIC_MARKDOWN", "E_ZIP_POLICY", "E_CODE_POLICY", "E_SOURCE_COPY"}.issubset(codes))

    def test_stale_sources_pdf_parity_fact_and_minute_content_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = make_manifest(5, Path(temporary))
            package = materialise_package(manifest)
            report_docx = package / manifest["artifacts"]["report"]["source_docx"]
            write_docx(report_docx, "Relatório alterado sem regenerar o PDF")
            css = package / "Entregaveis" / "Apresentacao" / "styles.css"
            css.write_text(".slide { color: red; }\n", encoding="utf-8")
            deck_pdf = package / manifest["artifacts"]["presentation"]["pdf"]
            write_fake_pdf(deck_pdf, [f"Título do slide {index}" for index in range(1, 5)])
            html_path = package / manifest["artifacts"]["presentation"]["html_entry"]
            html_path.write_text(html_path.read_text(encoding="utf-8").replace("1,0 u", "9,9 u"), encoding="utf-8")
            incomplete_minute = next(
                minute for minute in manifest["artifacts"]["minutes"] if minute["member_id"] == "pessoa2"
            )
            write_fake_pdf(package / incomplete_minute["understanding_pdf"], ["Pessoa Dois sem conteúdo obrigatório"])
            codes = issue_codes(validate_package(manifest, package))
            self.assertTrue(
                {
                    "E_STALE_REPORT_PDF",
                    "E_STALE_PRESENTATION_PDF",
                    "E_HTML_PDF_PARITY",
                    "E_FACT_MISMATCH",
                    "E_MINUTE_CONTENT",
                }.issubset(codes)
            )

    def test_required_code_needs_declared_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = make_manifest(5, Path(temporary))
            manifest["delivery"]["code"].update(
                {
                    "rubric": "required",
                    "reproducibility": "not_required",
                    "include": True,
                    "external_dependencies": ["numpy>=2"],
                }
            )
            package = materialise_package(manifest)
            code = package / "Entregaveis" / "Codigo"
            code.mkdir(parents=True)
            (code / "codigo.py").write_text("import numpy\n", encoding="utf-8")
            self.assertIn("E_CODE_REQUIREMENTS", issue_codes(validate_package(manifest, package)))
            (code / "requirements.txt").write_text("numpy>=2\n", encoding="utf-8")
            self.assertNotIn("E_CODE_REQUIREMENTS", issue_codes(validate_package(manifest, package)))

    def test_remote_runtime_dependency_fails_offline_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = make_manifest(5, Path(temporary))
            package = materialise_package(manifest)
            html_path = package / manifest["artifacts"]["presentation"]["html_entry"]
            html_path.write_text(
                html_path.read_text(encoding="utf-8").replace(
                    "</body>", '<img src="https://example.com/chart.png"></body>'
                ),
                encoding="utf-8",
            )
            manifest["provenance"]["presentation_bundle_sha256_at_pdf_generation"] = compute_bundle_sha256(
                package, manifest["artifacts"]["presentation"]["source_bundle"]
            )
            self.assertIn("E_OFFLINE_RESOURCE", issue_codes(validate_package(manifest, package)))


if __name__ == "__main__":
    unittest.main()
