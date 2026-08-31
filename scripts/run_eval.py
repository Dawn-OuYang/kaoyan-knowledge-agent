from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_engine import KaoyanAgent, KnowledgeBase

EVAL_PATH = ROOT / "data" / "eval_questions.json"
EXTENDED_EVAL_PATH = ROOT / "data" / "eval_questions_extended.json"
OUT_PATH = ROOT / "reports" / "rule_regression_log_local.md"


def score_case(case: dict, result: dict) -> dict:
    answer = result["answer"]
    citations = result.get("citations", [])
    citation_titles = [item["title"] for item in citations]
    expected_citation = case["expected_citation"]
    keywords = case["expected_keywords"]

    citation_hit = any(expected_citation in title for title in citation_titles)
    keyword_hits = sum(1 for keyword in keywords if keyword in answer)
    fact_score = 2 if keyword_hits >= max(1, len(keywords) - 1) else 1 if keyword_hits else 0
    citation_score = 2 if citation_hit else 0
    scene_score = 2 if result.get("route") else 0
    needs_warning = any(word in case["question"] for word in ["今年", "最新", "招生人数", "分数线", "参考书"])
    warning_score = 2 if not needs_warning or result.get("warnings") else 0
    expression_score = 2 if len(answer) >= 40 else 1 if answer else 0
    total = fact_score + citation_score + scene_score + warning_score + expression_score

    return {
        "fact_score": fact_score,
        "citation_score": citation_score,
        "scene_score": scene_score,
        "warning_score": warning_score,
        "expression_score": expression_score,
        "total": total,
        "passed": total >= 8,
        "citation_titles": citation_titles,
        "answer_summary": answer.replace("\n", " ")[:90],
    }


def main() -> None:
    kb = KnowledgeBase(ROOT / "data" / "knowledge_base.json")
    agent = KaoyanAgent(kb)
    cases = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    if EXTENDED_EVAL_PATH.exists():
        cases.extend(json.loads(EXTENDED_EVAL_PATH.read_text(encoding="utf-8")))

    rows = []
    passed = 0
    citation_full = 0
    warning_applicable = 0
    warning_full = 0
    total_score = 0
    mode_totals: dict[str, int] = {}
    mode_passed: dict[str, int] = {}

    for case in cases:
        result = agent.answer(case["question"], specialty=case["specialty"], mode=case["mode"])
        scores = score_case(case, result)
        passed += int(scores["passed"])
        citation_full += int(scores["citation_score"] == 2)
        total_score += scores["total"]
        mode_totals[case["mode"]] = mode_totals.get(case["mode"], 0) + 1
        mode_passed[case["mode"]] = mode_passed.get(case["mode"], 0) + int(scores["passed"])
        needs_warning = any(word in case["question"] for word in ["今年", "最新", "招生人数", "分数线", "参考书"])
        warning_applicable += int(needs_warning)
        warning_full += int(needs_warning and scores["warning_score"] == 2)
        rows.append((case, scores))

    lines = [
        "# 本地规则回归测试日志",
        "",
        "项目名称：考研各专业知识库问答智能体",
        "",
        "说明：本日志只验证固定样例上的检索引用、关键词覆盖、Agent路由、风险提示和回答长度，属于工程回归测试，不等价于模型精度、人工事实一致性或泛化能力。正式昇腾 NPU/Qwen3.5 精度结果需在昇腾环境按官方流程复测。",
        "",
        "| 编号 | 模式 | 输入问题 | 期望依据 | 实际输出摘要 | 事实一致性 | 引用命中 | 场景完整性 | 风险提示 | 表达可用性 | 总分 | 是否通过 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for case, scores in rows:
        lines.append(
            "| {id} | {mode} | {question} | {expected} | {summary} | {fact} | {citation} | {scene} | {warning} | {expr} | {total} | {passed} |".format(
                id=case["id"],
                mode=case["mode"],
                question=case["question"],
                expected=case["expected_citation"],
                summary=scores["answer_summary"].replace("|", "/"),
                fact=scores["fact_score"],
                citation=scores["citation_score"],
                scene=scores["scene_score"],
                warning=scores["warning_score"],
                expr=scores["expression_score"],
                total=scores["total"],
                passed="通过" if scores["passed"] else "未通过",
            )
        )

    total_cases = len(cases)
    avg_score = total_score / total_cases if total_cases else 0
    warning_rate = f"{warning_full}/{warning_applicable}" if warning_applicable else "无涉及时效样例"
    lines.extend(
        [
            "",
            "## 规则回归汇总",
            "",
            "| 指标 | 结果 |",
            "| --- | --- |",
            f"| 样例总数 | {total_cases} |",
            f"| 通过率 | {passed}/{total_cases} = {passed / total_cases:.1%} |",
            f"| 平均分 | {avg_score:.2f}/10 |",
            f"| 引用命中率 | {citation_full}/{total_cases} = {citation_full / total_cases:.1%} |",
            f"| 风险提示正确率 | {warning_rate} |",
        ]
    )
    lines.extend(["", "## 分场景通过率", "", "| 场景 | 通过 | 总数 | 通过率 |", "| --- | --- | --- | --- |"]) 
    for mode in sorted(mode_totals):
        lines.append(
            f"| {mode} | {mode_passed[mode]} | {mode_totals[mode]} | {mode_passed[mode] / mode_totals[mode]:.1%} |"
        )

    OUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote evaluation report to {OUT_PATH}")


if __name__ == "__main__":
    main()
