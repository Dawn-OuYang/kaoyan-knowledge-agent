from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from model_gateway import ModelGateway
from rag_engine import KaoyanAgent, KnowledgeBase


CASES = [
    {
        "mode": "school",
        "specialty": "全部",
        "question": "沈阳工业大学考研信息应该看哪些官方来源？",
        "answer": "应核验研招网院校库、招生简章、学校官网和研究生院官网。",
        "required": ["sut.edu.cn", "yjsxy.sut.edu.cn"],
    },
    {
        "mode": "school",
        "specialty": "全部",
        "question": "上海交通大学计算机方向应该优先核验哪个学院官网吗？",
        "answer": "上海交通大学计算机学院官网为优先核验对象。",
        "required": ["cs.sjtu.edu.cn", "研究生招生网"],
    },
    {
        "mode": "qa",
        "specialty": "计算机",
        "question": "DNS 递归查询和迭代查询在解析中怎样配合？",
        "answer": "递归查询和迭代查询配合完成解析，并通过缓存提高效率。",
        "required": ["本地 DNS", "根", "权威 DNS"],
    },
    {
        "mode": "plan",
        "specialty": "法学",
        "question": "法学错题本应该怎样分类和回炉？",
        "answer": "错题回炉时先独立重做，再补写错误原因。",
        "required": ["概念不清", "审题偏差", "独立重做", "错误原因"],
        "top_citation": "错题标签与回炉",
    },
    {
        "mode": "qa",
        "specialty": "通信工程",
        "question": "信号与系统中卷积的物理意义是什么？",
        "answer": "卷积是线性时不变系统输入与冲激响应共同决定输出的过程，连续系统输出为输入与冲激响应的卷积积分，离散系统输出为卷积和。",
        "required": [],
    },
    {
        "mode": "exam",
        "specialty": "法学",
        "question": "案例分析题中犯罪构成应该从哪些方面展开？",
        "answer": "案例分析题中犯罪构成应从客体、客观方面、主体、主观方面四个维度展开，需依次判断各要件是否具备。",
        "required": [],
    },
    {
        "mode": "exam",
        "specialty": "法学",
        "question": "合同效力案例题应该按什么顺序分析？",
        "answer": "按主体能力、意思表示和内容合法性，再审查特别事由。",
        "required": ["无效", "可撤销"],
        "top_citation": "合同效力分析",
    },
    {
        "mode": "plan",
        "specialty": "计算机",
        "question": "我总是看懂却记不住，怎样用主动回忆改进408复习？",
        "answer": "建议把每章转成问题清单，每日复述并重复自测。",
        "required": ["口述", "默写"],
        "top_citation": "主动回忆学习法",
    },
    {
        "mode": "exam",
        "specialty": "计算机",
        "question": "死锁产生的四个必要条件是什么？",
        "answer": "死锁产生的四个必要条件为互斥、请求保持、不可剥夺和循环等待。",
        "required": ["请求并保持"],
        "top_citation": "死锁必要条件",
    },
    {
        "mode": "exam",
        "specialty": "法学",
        "question": "直接故意、间接故意、疏忽大意和过于自信怎样区分？",
        "answer": "直接故意是明知并希望结果发生，间接故意是明知并放任结果发生；疏忽大意是应当预见而未预见，过于自信是已经预见但轻信能够避免。",
        "required": [],
        "top_citation": "犯罪故意与过失",
    },
]


def main() -> None:
    kb = KnowledgeBase(ROOT / "data" / "knowledge_base.json")
    agent = KaoyanAgent(kb)
    gateway = ModelGateway()

    for case in CASES:
        docs = agent._relevant_docs(kb.search(case["question"], specialty=case["specialty"], limit=5))
        if case["mode"] == "school":
            docs = agent._school_docs(case["question"], docs)
        elif case["mode"] == "plan":
            docs = agent._with_planning_docs(docs)

        expected_top = case.get("top_citation")
        if expected_top and docs[0]["title"] != expected_top:
            raise AssertionError(f"Unexpected top citation: {docs[0]['title']}")

        gaps = gateway._coverage_gaps(case["answer"], case["question"], case["mode"], docs[:3])
        repaired = gateway._append_grounded_evidence(case["answer"], gaps)
        missing = [term for term in case["required"] if term not in repaired]
        if missing:
            raise AssertionError(f"{case['question']}: missing {missing}; answer={repaired}")
        if not case["required"] and gaps:
            raise AssertionError(f"Unexpected repair for complete answer: {case['question']}: {gaps}")
        print(f"PASS: {case['mode']} - {case['question']}")

    print(f"Grounding coverage: {len(CASES)}/{len(CASES)} passed")
    malformed = "入口为 [https://example.edu.cn/，请交叉核验。](https://example.edu.cn/，请交叉核验。)"
    normalized = gateway._normalize_links(malformed)
    assert "[" not in normalized and "](" not in normalized and "https://example.edu.cn/" in normalized
    print("URL normalization: PASS")

    repaired_link = gateway._append_grounded_evidence("请核验官方来源。", [malformed])
    normalized_repair = gateway._normalize_links(repaired_link)
    assert "[" not in normalized_repair and "](" not in normalized_repair
    assert "https://example.edu.cn/" in normalized_repair
    print("Repaired URL normalization: PASS")

    repeated = "需以当年官方通知为准。[1] 请交叉核验官网。[1] 请交叉核验官网。"
    deduplicated = gateway._deduplicate_sentences(repeated)
    assert deduplicated.count("请交叉核验官网") == 1
    print("Sentence deduplication: PASS")

    comma_facts = gateway._enumerated_facts("常见方法包括方法一，方法二，方法三")
    assert comma_facts == ["方法一", "方法二", "方法三"]
    print("Comma enumeration: PASS")


if __name__ == "__main__":
    main()
