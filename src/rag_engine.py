from __future__ import annotations

import json
import math
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from model_gateway import ModelGateway


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


def tokenize(text: str) -> list[str]:
    raw = TOKEN_RE.findall(text.lower())
    grams: list[str] = []
    chinese_buffer: list[str] = []
    for token in raw:
        if re.fullmatch(r"[\u4e00-\u9fff]", token):
            chinese_buffer.append(token)
        else:
            if len(chinese_buffer) >= 2:
                grams.extend("".join(chinese_buffer[i : i + 2]) for i in range(len(chinese_buffer) - 1))
            grams.extend(chinese_buffer)
            chinese_buffer = []
            grams.append(token)
    if len(chinese_buffer) >= 2:
        grams.extend("".join(chinese_buffer[i : i + 2]) for i in range(len(chinese_buffer) - 1))
    grams.extend(chinese_buffer)
    return [g for g in grams if g.strip()]


@dataclass
class Document:
    id: str
    specialty: str
    subject: str
    title: str
    source: str
    content: str
    source_url: str = ""
    school: str = ""
    major: str = ""
    year: str = ""
    published_at: str = ""
    retrieved_at: str = ""
    risk_level: str = "stable"
    source_type: str = "curated_reference"


class KnowledgeBase:
    def __init__(self, path: Path):
        data = json.loads(path.read_text(encoding="utf-8"))
        expansion_path = path.with_name("knowledge_expansion.json")
        if expansion_path.exists():
            data.extend(json.loads(expansion_path.read_text(encoding="utf-8")))

        metadata_path = path.with_name("source_cards_sample.json")
        metadata_by_id: dict[str, dict[str, Any]] = {}
        if metadata_path.exists():
            metadata_by_id = {
                item["id"]: item for item in json.loads(metadata_path.read_text(encoding="utf-8"))
            }
        data = [{**item, **metadata_by_id.get(item["id"], {})} for item in data]

        deduplicated = {item["id"]: item for item in data}
        fields = Document.__dataclass_fields__
        self.docs = [
            Document(**{key: value for key, value in item.items() if key in fields})
            for item in deduplicated.values()
        ]
        self.doc_tokens = {doc.id: Counter(tokenize(" ".join([doc.title, doc.subject, doc.content]))) for doc in self.docs}
        self.idf = self._build_idf()

    def specialties(self) -> list[str]:
        values = sorted({doc.specialty for doc in self.docs if doc.specialty != "通用"})
        return ["全部", *values]

    def search(self, question: str, specialty: str = "全部", limit: int = 4) -> list[dict[str, Any]]:
        q_tokens = Counter(tokenize(question))
        if not q_tokens:
            return []

        scored = []
        for doc in self.docs:
            if specialty not in ("全部", "", None) and doc.specialty not in (specialty, "通用"):
                continue
            score = self._score(q_tokens, self.doc_tokens[doc.id])
            if specialty and doc.specialty == specialty:
                score *= 1.18
            if score > 0:
                scored.append((score, doc))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "id": doc.id,
                "score": round(score, 4),
                "specialty": doc.specialty,
                "subject": doc.subject,
                "title": doc.title,
                "source": doc.source,
                "source_url": doc.source_url,
                "school": doc.school,
                "major": doc.major,
                "year": doc.year,
                "published_at": doc.published_at,
                "retrieved_at": doc.retrieved_at,
                "risk_level": doc.risk_level,
                "source_type": doc.source_type,
                "content": doc.content,
            }
            for score, doc in scored[:limit]
        ]

    def _build_idf(self) -> dict[str, float]:
        df: defaultdict[str, int] = defaultdict(int)
        for tokens in self.doc_tokens.values():
            for token in tokens:
                df[token] += 1
        total = len(self.docs)
        return {token: math.log((total + 1) / (freq + 0.5)) + 1 for token, freq in df.items()}

    def _score(self, query: Counter[str], doc: Counter[str]) -> float:
        score = 0.0
        doc_len = sum(doc.values()) or 1
        avg_len = sum(sum(tokens.values()) for tokens in self.doc_tokens.values()) / max(len(self.doc_tokens), 1)
        k1 = 1.4
        b = 0.72
        for token, qf in query.items():
            if token not in doc:
                continue
            tf = doc[token]
            idf = self.idf.get(token, 1.0)
            denom = tf + k1 * (1 - b + b * doc_len / avg_len)
            score += idf * (tf * (k1 + 1) / denom) * (1 + math.log(qf))
        return score


class KaoyanAgent:
    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.model_gateway = ModelGateway()

    def answer(self, question: str, specialty: str = "全部", mode: str = "qa", profile: dict[str, Any] | None = None) -> dict[str, Any]:
        started = time.perf_counter()
        retrieval_started = time.perf_counter()
        retrieval_question = self._retrieval_question(question, mode)
        docs = self._relevant_docs(self.kb.search(retrieval_question, specialty=specialty, limit=5))
        if mode == "exam":
            answer = self._exam_answer(question, docs)
            route = "真题解析 Agent"
        elif mode == "plan":
            docs = self._with_planning_docs(docs)
            answer = self._plan_answer(question, specialty, profile or {}, docs)
            route = "复习规划 Agent"
        elif mode == "school":
            docs = self._school_docs(question, docs)
            answer = self._school_answer(question, docs)
            route = "院校咨询 Agent"
        else:
            answer = self._qa_answer(question, docs)
            route = "知识问答 Agent"

        retrieval_ms = (time.perf_counter() - retrieval_started) * 1000
        model_result = self.model_gateway.generate(question, mode, docs[:3], answer)
        confidence = self._confidence(docs)
        total_ms = (time.perf_counter() - started) * 1000
        return {
            "route": route,
            "answer": model_result["text"],
            "confidence": confidence,
            "citations": docs[:3],
            "warnings": self._warnings(question, docs),
            "model_provider": model_result["provider"],
            "model_error": model_result["error"],
            "model_usage": model_result["usage"],
            "timings": {
                "retrieval_ms": round(retrieval_ms, 2),
                "generation_ms": model_result["latency_ms"],
                "total_ms": round(total_ms, 2),
            },
            "evidence": {
                "citation_count": min(3, len(docs)),
                "url_count": sum(1 for doc in docs[:3] if doc.get("source_url")),
                "time_sensitive_count": sum(1 for doc in docs[:3] if doc.get("risk_level") == "time_sensitive"),
            },
        }

    @staticmethod
    def _relevant_docs(docs: list[dict[str, Any]], relative_threshold: float = 0.7) -> list[dict[str, Any]]:
        if not docs:
            return []
        threshold = float(docs[0]["score"]) * relative_threshold
        return [doc for doc in docs if float(doc["score"]) >= threshold]

    @staticmethod
    def _retrieval_question(question: str, mode: str) -> str:
        if mode != "exam":
            return question
        cleaned = re.sub(r"^\s*(?:真题解析|题目解析|试题解析)\s*[：:]?\s*", "", question)
        return cleaned or question

    def invoke_skill(self, payload: dict[str, Any]) -> dict[str, Any]:
        question = str(payload.get("question", "")).strip()
        if not question:
            raise ValueError("question is required")
        specialty = str(payload.get("specialty", "全部")).strip() or "全部"
        mode = str(payload.get("mode", "qa")).strip() or "qa"
        profile = payload.get("profile") if isinstance(payload.get("profile"), dict) else {}
        result = self.answer(question, specialty=specialty, mode=mode, profile=profile)
        return {
            "skill_name": "kaoyan_knowledge_agent",
            "skill_version": "0.3.0",
            "input": {
                "question": question,
                "specialty": specialty,
                "mode": mode,
                "profile": profile,
            },
            "output": result,
            "ascend_ready": {
                "model_adapter": "KAOYAN_MODEL_ENDPOINT + Qwen Chat protocol",
                "target_framework": "MindSpeed-MM + Qwen3.5",
                "npu_runtime": "Ascend CANN / torch_npu",
                "model_connected": self.model_gateway.enabled,
            },
        }

    def _with_planning_docs(self, docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        planning_docs = [doc for doc in docs if doc.get("subject") == "复习规划"]
        other_docs = [doc for doc in docs if doc.get("subject") != "复习规划"]
        combined = list(planning_docs)
        seen = {doc["id"] for doc in combined}
        for doc in self.kb.search("三阶段复习框架 基础 强化 冲刺 复习规划", specialty="通用", limit=3):
            if doc["id"] not in seen:
                combined.append(doc)
                seen.add(doc["id"])
        combined.extend(doc for doc in other_docs if doc["id"] not in seen)
        return combined

    def _school_docs(self, question: str, docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        school_names = ["清华大学", "北京理工大学", "上海交通大学", "沈阳工业大学"]
        direction_words = {
            "计算机": ["计算机", "408", "计算机科学"],
            "通信工程": ["通信", "电子工程", "信息与电子"],
            "法学": ["法学", "法学院"],
        }
        target_schools = [name for name in school_names if name in question]
        target_directions = [name for name, words in direction_words.items() if any(word in question for word in words)]

        by_id = {doc["id"]: doc for doc in docs}
        if target_schools or target_directions:
            query = " ".join([question, *target_schools, *target_directions, "研究生招生 学院 官网 研招网"])
            for doc in self.kb.search(query, specialty="全部", limit=12):
                by_id.setdefault(doc["id"], doc)

        candidates = [doc for doc in by_id.values() if doc["subject"] != "项目范围"]

        if target_schools:
            school_candidates = [doc for doc in candidates if doc.get("school") in target_schools]

            def matches_direction(doc: dict[str, Any]) -> bool:
                structured = " ".join(
                    [doc.get("specialty", ""), doc.get("major", ""), doc.get("title", "")]
                )
                return any(
                    direction in structured
                    or any(word in structured for word in direction_words[direction])
                    for direction in target_directions
                )

            if target_directions:
                direction_docs = [doc for doc in school_candidates if matches_direction(doc)]
                school_sources = [
                    doc
                    for doc in school_candidates
                    if doc.get("subject") == "院校信息" and not doc.get("major")
                ]
                selected = [*direction_docs, *school_sources]
            else:
                selected = [
                    doc
                    for doc in school_candidates
                    if doc.get("subject") in ("院校信息", "招生简章", "硕士目录")
                ]
                if not selected:
                    selected = school_candidates

            selected.sort(
                key=lambda doc: (
                    doc.get("subject") != "学院信息" if target_directions else doc.get("subject") != "院校信息",
                    -float(doc["score"]),
                )
            )
            deduplicated: list[dict[str, Any]] = []
            seen: set[str] = set()
            for doc in selected:
                if doc["id"] not in seen:
                    deduplicated.append(doc)
                    seen.add(doc["id"])
            return deduplicated[:3]

        def boosted_score(doc: dict[str, Any]) -> float:
            haystack = " ".join([doc["title"], doc["source"], doc["content"]])
            score = float(doc["score"])
            if target_schools:
                if any(school in haystack for school in target_schools):
                    score += 100
                else:
                    score -= 25
            if target_directions:
                if any(direction in haystack for direction in target_directions):
                    score += 40
                elif any(word in haystack for direction in target_directions for word in direction_words[direction]):
                    score += 25
                else:
                    score -= 60
            if doc["subject"] in ("学院信息", "院校信息", "硕士目录", "招生简章"):
                score += 8
            return score

        ranked = sorted(candidates, key=boosted_score, reverse=True)

        def has_school(doc: dict[str, Any]) -> bool:
            haystack = " ".join([doc["title"], doc["source"], doc["content"]])
            return bool(target_schools) and any(school in haystack for school in target_schools)

        def has_direction(doc: dict[str, Any]) -> bool:
            haystack = " ".join([doc["title"], doc["source"], doc["content"]])
            return bool(target_directions) and any(
                direction in haystack or any(word in haystack for word in direction_words[direction])
                for direction in target_directions
            )

        priority_groups = [
            [doc for doc in ranked if has_school(doc) and has_direction(doc)],
            [doc for doc in ranked if has_school(doc) and not has_direction(doc)],
            [doc for doc in ranked if has_direction(doc) and not has_school(doc)],
            [doc for doc in ranked if not has_school(doc) and not has_direction(doc)],
        ]
        ranked = []
        seen: set[str] = set()
        for group in priority_groups:
            for doc in group:
                if doc["id"] not in seen:
                    ranked.append(doc)
                    seen.add(doc["id"])
        return self._relevant_docs(ranked[:5])

    def _qa_answer(self, question: str, docs: list[dict[str, Any]]) -> str:
        if not docs:
            return "当前知识库没有检索到足够依据。建议补充目标专业的大纲、教材章节或真题解析后再回答。"
        bullets = []
        for doc in docs[:3]:
            bullets.append(f"- {doc['title']}：{self._compress(doc['content'])}")
        return (
            "根据已收录资料，可以这样回答：\n"
            + "\n".join(bullets)
            + "\n\n建议继续追问具体题型、年份或目标院校，我可以把答案拆成考点、易错点和背诵版。"
        )

    def _exam_answer(self, question: str, docs: list[dict[str, Any]]) -> str:
        base = self._qa_answer(question, docs)
        return (
            "【考点定位】\n"
            f"{base}\n\n"
            "【作答结构】\n"
            "1. 先写核心概念、公式或判定标准。\n"
            "2. 再说明适用条件、关键步骤或构成要件。\n"
            "3. 最后补充易错点，并用题干信息回扣结论。\n\n"
            "【易错提醒】\n"
            "如果题目包含年份、院校或特殊限定条件，应优先按对应考试大纲和真题口径作答。"
        )

    def _school_answer(self, question: str, docs: list[dict[str, Any]]) -> str:
        return (
            "院校相关问题需要优先引用目标院校研究生院、学院官网和研招网正式入口。\n\n"
            + self._qa_answer(question, docs)
            + "\n\n【信息核验】涉及招生人数、复试线、参考书和考试科目时，请补充具体学校、学院、专业代码和年份，系统会把回答限定到对应来源。"
        )

    def _plan_answer(self, question: str, specialty: str, profile: dict[str, Any], docs: list[dict[str, Any]]) -> str:
        days = str(profile.get("days") or self._extract_days(question) or "120")
        level = str(profile.get("level") or "基础一般")
        target = str(profile.get("target") or "目标院校未填写")
        evidence = "\n".join(
            f"- {doc['title']}：{self._compress(doc['content'], limit=120)}" for doc in docs[:3]
        )
        return (
            f"为 {target} 制定 {days} 天复习计划，当前基础：{level}，专业方向：{specialty}。\n\n"
            "【阶段一：基础建立】\n"
            "梳理考试大纲、教材目录和高频知识点，每天完成知识点输入与简短复述。\n\n"
            "【阶段二：强化训练】\n"
            "按章节刷真题和典型题，建立错题标签：概念不清、步骤缺失、审题偏差、记忆遗漏。\n\n"
            "【阶段三：冲刺回炉】\n"
            "进行限时模拟、错题回炉和答题模板稳定，重点复盘近年真题与目标院校偏好。\n\n"
            "【本周动作】\n"
            "1. 上传或整理目标专业大纲。\n"
            "2. 建立章节知识库。\n"
            "3. 每天用 3 个问题检测当日知识点。\n\n"
            "【参考方法】\n" + (evidence or "- 通用三阶段复习框架")
        )

    @staticmethod
    def _extract_days(question: str) -> str | None:
        match = re.search(r"(\d{1,3})\s*天", question)
        if match:
            return match.group(1)
        if "冲刺" in question:
            return "30"
        return None

    def _confidence(self, docs: list[dict[str, Any]]) -> str:
        if not docs:
            return "低"
        top = docs[0]["score"]
        if top >= 8:
            return "高"
        if top >= 3:
            return "中"
        return "低"

    def _warnings(self, question: str, docs: list[dict[str, Any]]) -> list[str]:
        warnings = []
        if not docs:
            warnings.append("未检索到引用依据，回答应视为待补充。")
        if any(word in question for word in ["今年", "最新", "分数线", "招生人数", "参考书", "复试"]):
            warnings.append("该问题可能涉及年度变化，请以目标院校当年官方通知为准。")
        return warnings

    @staticmethod
    def _compress(text: str, limit: int = 95) -> str:
        return text if len(text) <= limit else text[:limit] + "..."
