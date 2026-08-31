from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_engine import KaoyanAgent, KnowledgeBase


CASES = [
    {
        "name": "knowledge qa",
        "payload": {"question": "顺序表和链表的区别是什么？", "specialty": "计算机", "mode": "qa"},
        "must_contain": ["链表", "顺序表"],
    },
    {
        "name": "exam analysis",
        "payload": {"question": "真题解析：为什么 TCP 建立连接需要三次握手？", "specialty": "计算机", "mode": "exam"},
        "must_contain": ["考点定位", "作答结构"],
    },
    {
        "name": "school warning",
        "payload": {"question": "今年清华大学计算机专业招生人数是多少？", "specialty": "全部", "mode": "school"},
        "must_contain": ["官方", "招生人数"],
    },
    {
        "name": "planning",
        "payload": {
            "question": "距离考试 90 天，通信工程专业课怎么安排？",
            "specialty": "通信工程",
            "mode": "plan",
            "profile": {"target": "北京理工大学", "days": "90", "level": "基础一般"},
        },
        "must_contain": ["基础", "强化", "冲刺"],
    },
]


def main() -> None:
    kb = KnowledgeBase(ROOT / "data" / "knowledge_base.json")
    agent = KaoyanAgent(kb)
    rows = []
    failures = []

    for case in CASES:
        result = agent.invoke_skill(case["payload"])
        output = result["output"]
        text = output["answer"] + " " + " ".join(output.get("warnings", []))
        ok = bool(output.get("citations")) and all(item in text for item in case["must_contain"])
        rows.append(
            {
                "case": case["name"],
                "route": output.get("route"),
                "confidence": output.get("confidence"),
                "citations": [item["title"] for item in output.get("citations", [])],
                "passed": ok,
            }
        )
        if not ok:
            failures.append(case["name"])

    report = ROOT / "reports" / "functional_test_log.md"
    lines = [
        "# 功能验证日志",
        "",
        "说明：本日志验证本地 Skill Runtime 的四类核心场景。正式复赛需在昇腾 NPU 环境补充模型推理链路验证。",
        "",
        "| 用例 | Agent 路由 | 置信度 | 引用 | 是否通过 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {case} | {route} | {confidence} | {citations} | {passed} |".format(
                case=row["case"],
                route=row["route"],
                confidence=row["confidence"],
                citations="、".join(row["citations"]),
                passed="通过" if row["passed"] else "未通过",
            )
        )
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"passed": len(CASES) - len(failures), "total": len(CASES), "failures": failures}, ensure_ascii=False))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
