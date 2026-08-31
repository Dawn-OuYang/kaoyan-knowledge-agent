from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_PATH = ROOT / "ascend" / "annotations_slim.json"
MANIFEST_PATH = ROOT / "ascend" / "dataset_manifest.json"


QUESTION_TEMPLATES = {
    "学院信息": [
        "{title}应如何核验？",
        "查询{title}时要保留哪些官方来源信息？",
        "请按考研院校咨询口径说明{title}，并提示时效风险。",
    ],
    "院校信息": [
        "{title}应如何核验？",
        "查询{title}时应优先看哪些官方来源？",
        "请说明{title}的使用边界和时效风险。",
    ],
    "复习规划": [
        "请根据考研备考场景说明：{title}。",
        "怎样把{title}落实到一周复习安排？",
        "使用{title}时有哪些容易忽略的执行要点？",
    ],
}


def load_items() -> list[dict]:
    items = json.loads((DATA_DIR / "knowledge_base.json").read_text(encoding="utf-8"))
    expansion = DATA_DIR / "knowledge_expansion.json"
    if expansion.exists():
        items.extend(json.loads(expansion.read_text(encoding="utf-8")))

    metadata = json.loads((DATA_DIR / "source_cards_sample.json").read_text(encoding="utf-8"))
    metadata_by_id = {item["id"]: item for item in metadata}
    merged = [{**item, **metadata_by_id.get(item["id"], {})} for item in items]
    return list({item["id"]: item for item in merged}.values())


def questions_for(item: dict) -> list[str]:
    templates = QUESTION_TEMPLATES.get(
        item["subject"],
        [
            "请用考研答题口径说明：{title}。",
            "{title}有哪些核心概念、适用条件和易错点？",
            "如果在考研题目中遇到{title}，应怎样组织答案？",
        ],
    )
    return [template.format(title=item["title"]) for template in templates]


def answer_for(item: dict) -> str:
    source_line = f"来源：{item['source']}"
    if item.get("source_url"):
        source_line += f"（{item['source_url']}）"
    if item.get("year"):
        source_line += f"；年份：{item['year']}"
    if item.get("retrieved_at"):
        source_line += f"；采集日期：{item['retrieved_at']}"
    warning = " 涉及时效信息时，应以对应年份官方通知为准。" if item.get("risk_level") == "time_sensitive" else ""
    return f"{item['content']}\n\n{source_line}。{warning}"


def main() -> None:
    items = load_items()
    samples = []
    for item in items:
        for question in questions_for(item):
            samples.append(
                {
                    "images": [],
                    "messages": [
                        {"role": "user", "content": question},
                        {"role": "assistant", "content": answer_for(item)},
                    ],
                    "metadata": {
                        "knowledge_id": item["id"],
                        "specialty": item["specialty"],
                        "subject": item["subject"],
                        "source_type": item.get("source_type", "curated_reference"),
                    },
                }
            )

    OUT_PATH.write_text(json.dumps(samples, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "generated_at": "2026-07-21",
        "knowledge_items": len(items),
        "samples": len(samples),
        "samples_per_item": 3,
        "specialties": Counter(item["specialty"] for item in items),
        "source_types": Counter(item.get("source_type", "curated_reference") for item in items),
        "claim": "curated and synthetic SFT data; not an official full admissions database",
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(samples)} samples from {len(items)} knowledge items to {OUT_PATH}")


if __name__ == "__main__":
    main()
