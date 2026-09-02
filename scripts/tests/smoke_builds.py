#!/usr/bin/env python3
"""Integration smoke test for the DOCX, study-PDF and variable HTML deck pipelines."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
SKILL_DIR = SCRIPTS_DIR.parent
for value in (str(TESTS_DIR), str(SCRIPTS_DIR)):
    if value not in sys.path:
        sys.path.insert(0, value)

from generate_deck_data import build_deck_data  # noqa: E402
from manifest_lib import file_sha256, matrix_digest  # noqa: E402
from test_manifest import make_manifest  # noqa: E402


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def expand_to_seven_slides(manifest: dict) -> None:
    specs = [
        ("S01", 1, "B1", "Por que este problema exige comparação", [], 35),
        ("S02", 2, "B1", "Dados, entrada e saída", ["Q1"], 55),
        ("S03", 3, "B2", "Três famílias candidatas", ["Q2"], 75),
        ("S04", 4, "B3", "As métricas medem aspectos diferentes", ["Q3"], 65),
        ("S05", 5, "B3", "O diagnóstico organiza as evidências", [], 45),
        ("S06", 6, "B4", "O gráfico revela a forma do erro", ["Q4"], 75),
        ("S07", 7, "B5", "A decisão vale dentro do domínio", ["Q5"], 60),
    ]
    block_facts = {block["id"]: block.get("fact_ids", []) for block in manifest["blocks"]}
    manifest["slides"] = [
        {
            "id": slide_id,
            "ordinal": ordinal,
            "title": title,
            "owner_block_id": block_id,
            "question_unit_ids": question_ids,
            "fact_ids": block_facts[block_id] if question_ids else [],
            "glossary_term_ids": ["T"],
            "seconds": seconds,
        }
        for slide_id, ordinal, block_id, title, question_ids, seconds in specs
    ]
    for block in manifest["blocks"]:
        owned = [slide for slide in manifest["slides"] if slide["owner_block_id"] == block["id"]]
        block["slide_ids"] = [slide["id"] for slide in owned]
        block["seconds"] = sum(slide["seconds"] for slide in owned)
    manifest["review_gate"]["matrix_sha256"] = matrix_digest(manifest)


def fill_deck(manifest: dict, destination: Path) -> None:
    data = build_deck_data(manifest)
    slides = {slide["id"]: slide for slide in data["slides"]}
    slides["S01"].update(
        layout="cover",
        eyebrow="PROBLEMA DE TESTE",
        lead="Como comparar modelos com estruturas e complexidades diferentes?",
        notes="Apresentar a pergunta central sem antecipar o vencedor.",
        transition="Agora identificamos os dados usados na comparação.",
    )
    slides["S02"].update(
        layout="content",
        bodyHtml=(
            "<p>A entrada é <b>x</b>; a saída observada é <b>y</b>.</p>"
            "<table><thead><tr><th>x</th><th>y</th><th>unidade</th></tr></thead>"
            "<tbody><tr><td>0</td><td>1,0</td><td>u</td></tr><tr><td>1</td><td>1,8</td><td>u</td></tr></tbody></table>"
        ),
        notes="Distinguir entrada, saída observada e previsão.",
        transition="Com os dados definidos, apresentamos os candidatos.",
    )
    slides["S03"].update(
        layout="comparison",
        items=[
            {"label": "LINEAR", "formulaLatex": r"\hat y=a_0+a_1x", "reading": "Representa tendência sem curvatura."},
            {"label": "QUADRÁTICO", "formulaLatex": r"\hat y=a_0+a_1x+a_2x^2", "reading": "Acrescenta uma curvatura global."},
            {"label": "EXPONENCIAL", "formulaLatex": r"\hat y=Ae^{bx}", "reading": "Representa variação multiplicativa."},
        ],
        bodyHtml="<p>Os candidatos vêm do entendimento do problema; as métricas apenas testam essa escolha.</p>",
        notes="Comparar hipóteses, não apenas fórmulas.",
        transition="Depois do ajuste, quantificamos o erro.",
    )
    slides["S04"].update(
        layout="metrics",
        metrics=[
            {"termId": "SQR", "value": "0,041", "label": "SQR", "definition": "Erro total: soma dos resíduos ao quadrado."},
            {"termId": "RMSE", "value": "0,083 u", "label": "RMSE", "definition": "Tamanho típico do erro, na unidade da saída."},
            {"termId": "R2", "value": "0,982", "label": "R²", "definition": "Proporção da variação explicada."},
            {"termId": "R2A", "value": "0,974", "label": "R² ajustado", "definition": "Ganho considerando a quantidade de parâmetros."},
        ],
        takeaway="Nenhuma métrica, sozinha, escolhe o modelo.",
        notes="Conceituar cada sigla na primeira ocorrência.",
        transition="As métricas entram em um diagnóstico conjunto.",
    )
    slides["S05"].update(
        layout="flow",
        steps=[
            {"label": "Prever", "meaning": "Gerar ŷ para cada entrada."},
            {"label": "Comparar", "meaning": "Calcular observado menos previsto."},
            {"label": "Diagnosticar", "meaning": "Ver magnitude e padrão do erro."},
            {"label": "Decidir", "meaning": "Combinar evidência, custo e domínio."},
        ],
        notes="Mostrar como cada etapa depende da anterior.",
        transition="O gráfico torna o padrão dos erros visível.",
    )
    slides["S06"].update(
        layout="visual",
        visualHtml=(
            '<svg viewBox="0 0 720 360" role="img" aria-label="Resíduos ao redor de zero">'
            '<line x1="70" y1="180" x2="680" y2="180" stroke="#141414" stroke-width="3"/>'
            '<polyline points="90,235 205,145 320,120 435,165 550,215 665,195" fill="none" stroke="#2e74b5" stroke-width="6"/>'
            '<text x="75" y="40" font-size="24">resíduo = observado − previsto</text></svg>'
        ),
        caption="Mesma escala e linha zero: o formato do erro pode ser comparado diretamente.",
        evidence=[
            {"label": "Padrão", "text": "Tendência organizada indica estrutura não capturada."},
            {"label": "Magnitude", "text": "Distância da linha zero mostra o tamanho do erro."},
            {"label": "Limite", "text": "Resíduos não provam uma lei física."},
        ],
        notes="Explicar eixos, linha zero e padrão antes de concluir.",
        transition="A conclusão combina esse diagnóstico com as métricas.",
    )
    slides["S07"].update(
        layout="decision",
        resultLabel="DECISÃO DE TESTE",
        resultValue="Modelo compatível com os dados",
        lead="A recomendação combina aderência, resíduos, métricas e complexidade.",
        limit="Válida apenas na faixa analisada; fora dela, seria extrapolação.",
        notes="Encerrar com a decisão e seu domínio de validade.",
        transition="Encerramento.",
    )
    for slide in data["slides"]:
        slide.pop("bodyHtml", None) if slide["layout"] != "content" and "bodyHtml" in slide and "{{" in slide["bodyHtml"] else None
        slide.setdefault("notes", "Fala verificada.")
        slide.setdefault("transition", "Transição verificada.")
        slide.setdefault("sources", [])
    destination.write_text("window.MODELAGEM_DECK = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_root", type=Path)
    args = parser.parse_args()
    root = args.output_root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=False)
    manifest = make_manifest(5, root)
    expand_to_seven_slides(manifest)
    original = Path(manifest["source"]["original_path"])
    original.write_bytes(b"%PDF-1.4\n% smoke source\n%%EOF\n")
    manifest["source"]["original_sha256"] = file_sha256(original)
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    run([sys.executable, str(SCRIPTS_DIR / "scaffold_case.py"), str(manifest_path)])
    package = Path(manifest["project"]["package_root"])
    deck_root = package / "Entregaveis" / "Apresentacao"
    fill_deck(manifest, deck_root / "deck-data.js")

    source = Path(manifest["project"]["build_root"]) / "sources" / "smoke-study.md"
    source.write_text(
        """# Guia de teste — comparação de modelos

## Conceito

O resíduo mantém a definição $r_i=y_i-\\hat y_i$. A função de erro é:

\\[
J(a)=\\sum_{i=1}^{n}r_i^2=r^Tr
\\]

| Família | Forma | O que muda | Atenção |
|---|---|---|---|
| Linear | $\\hat y=a_0+a_1x$ | inclinação | sem curvatura |
| Quadrática | $\\hat y=a_0+a_1x+a_2x^2$ | termo $x^2$ | parâmetro extra |
| Exponencial | $\\hat y=Ae^{bx}$ | escala multiplicativa | erro depende da escala |

O texto `<script>alert('não executar')</script>` deve aparecer apenas como texto.
""",
        encoding="utf-8",
    )

    bundled_node = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
    node = os.environ.get("NODE_BIN") or shutil.which("node") or (str(bundled_node) if bundled_node.exists() else None)
    if not node:
        raise RuntimeError("Node.js não encontrado. Instale Node.js LTS ou informe NODE_BIN.")
    guide_pdf = package / manifest["artifacts"]["study_guide"]["pdf"]
    run([str(node), str(SCRIPTS_DIR / "build_study_pdf.cjs"), str(source), str(guide_pdf), "--manifest", str(manifest_path)])
    deck_pdf = package / manifest["artifacts"]["presentation"]["pdf"]
    run([str(node), str(SCRIPTS_DIR / "build_deck_pdf.cjs"), str(deck_root / "index.html"), str(deck_pdf), "--manifest", str(manifest_path)])

    report_docx = package / manifest["artifacts"]["report"]["source_docx"]
    report_pdf = package / manifest["artifacts"]["report"]["pdf"]
    report_qa = Path(manifest["project"]["build_root"]) / "qa" / "report"
    run([sys.executable, str(SCRIPTS_DIR / "build_report_pdf.py"), str(report_docx), str(report_pdf), "--qa-dir", str(report_qa), "--manifest", str(manifest_path)])

    print(json.dumps({"root": str(root), "guide_pdf": str(guide_pdf), "deck_pdf": str(deck_pdf), "report_pdf": str(report_pdf), "report_qa": str(report_qa)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
