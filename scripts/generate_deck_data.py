#!/usr/bin/env python3
"""Generate a variable-length deck-data.js starter from a validated manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from manifest_lib import load_manifest, question_text, validate_manifest


def build_deck_data(manifest: dict) -> dict:
    blocks = {block["id"]: block for block in manifest["blocks"]}
    people = {member["id"]: member["name"] for member in manifest["team"]}
    units = {
        unit["id"]: question_text(unit)
        for unit in manifest["problem"]["question_units"]
    }
    slides = []
    ordered = sorted(manifest["slides"], key=lambda item: item["ordinal"])
    for index, source in enumerate(ordered):
        block = blocks[source["owner_block_id"]]
        questions = [units[unit_id] for unit_id in source.get("question_unit_ids", [])]
        slide = {
            "id": source["id"],
            "ownerBlockId": source["owner_block_id"],
            "ownerName": people[block["member_id"]],
            "seconds": source["seconds"],
            "questionUnitIds": source.get("question_unit_ids", []),
            "layout": "cover" if index == 0 else "content",
            "eyebrow": block["title"].upper(),
            "title": source["title"],
            "lead": " ".join(questions),
            "bodyHtml": f"<p>{{{{CONTEUDO_VERIFICADO_{source['id']}}}}}</p>",
            "notes": f"{{{{FALA_VERIFICADA_{source['id']}}}}}",
            "transition": f"{{{{TRANSICAO_VERIFICADA_{source['id']}}}}}",
            "sources": [],
        }
        slides.append(slide)
    return {
        "title": manifest["project"]["title"],
        "course": "Modelagem Computacional",
        "identification": manifest["project"]["id"],
        "durationSeconds": manifest["delivery"]["duration"]["max_seconds"],
        "team": [member["name"] for member in manifest["team"]],
        "slides": slides,
    }


def write_deck_data(manifest: dict, destination: Path) -> None:
    payload = json.dumps(build_deck_data(manifest), ensure_ascii=False, indent=2)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(f"window.MODELAGEM_DECK = {payload};\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    data = load_manifest(args.manifest)
    issues = validate_manifest(data)
    if issues:
        for issue in issues:
            print(f"{issue.code}: {issue.message}")
        return 1
    destination = args.destination.expanduser().resolve()
    write_deck_data(data, destination)
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
