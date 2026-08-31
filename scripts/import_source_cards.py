from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KB_PATH = ROOT / "data" / "knowledge_base.json"
CARDS_PATH = ROOT / "data" / "source_cards_sample.json"


def main() -> None:
    kb_items = json.loads(KB_PATH.read_text(encoding="utf-8"))
    cards = json.loads(CARDS_PATH.read_text(encoding="utf-8"))
    existing_ids = {item["id"] for item in kb_items}

    added = 0
    for card in cards:
        if card["id"] in existing_ids:
            continue
        kb_items.append(card)
        added += 1

    KB_PATH.write_text(json.dumps(kb_items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Imported {added} source cards into {KB_PATH}")


if __name__ == "__main__":
    main()
