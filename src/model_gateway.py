from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class ModelGateway:
    """Bridge the Skill runtime to a Qwen3.5 inference endpoint."""

    def __init__(self) -> None:
        self.endpoint = os.environ.get("KAOYAN_MODEL_ENDPOINT", "").strip()
        self.timeout = float(os.environ.get("KAOYAN_MODEL_TIMEOUT", "60"))
        self.protocol = os.environ.get("KAOYAN_MODEL_PROTOCOL", "auto").strip().lower()
        self.model = os.environ.get("KAOYAN_MODEL_NAME", "Qwen3.5-0.8B").strip()
        self.api_key = os.environ.get("KAOYAN_MODEL_API_KEY", "").strip()

    @property
    def enabled(self) -> bool:
        return bool(self.endpoint)

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "protocol": self._resolved_protocol() if self.enabled else "local-template",
            "model": self.model if self.enabled else "local-template",
        }

    def generate(self, question: str, mode: str, contexts: list[dict[str, Any]], fallback: str) -> dict[str, Any]:
        if not self.enabled:
            return {
                "text": fallback,
                "provider": "local-template",
                "error": None,
                "latency_ms": 0.0,
                "usage": {},
            }

        started = time.perf_counter()
        protocol = self._resolved_protocol()
        payload = self._qwen_payload(question, mode, contexts) if protocol == "qwen" else self._native_payload(question, mode, contexts)
        headers = {"Content-Type": "application/json; charset=utf-8"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            request = urllib.request.Request(
                self.endpoint,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            return {
                "text": fallback,
                "provider": "local-template",
                "error": f"model gateway unavailable: {exc}",
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "usage": {},
            }

        text = self._deduplicate_sentences(self._normalize_links(self._extract_text(data, protocol)))
        if not text:
            return {
                "text": fallback,
                "provider": "local-template",
                "error": "model gateway returned empty text",
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "usage": data.get("usage", {}),
            }

        usage = dict(data.get("usage") or {})
        gaps = self._coverage_gaps(text, question, mode, contexts)
        if gaps:
            text = self._append_grounded_evidence(text, gaps)
            usage["grounding_repair"] = True
            usage["grounding_repair_count"] = len(gaps)
            usage["grounding_repair_source"] = "top_citation"
            usage["grounding_repair_mode"] = mode
        else:
            usage["grounding_repair"] = False
            usage["grounding_repair_count"] = 0

        text = self._normalize_links(text)
        text, insufficiency_repaired = self._repair_unsupported_admission_count(
            question, mode, contexts, text
        )
        usage["evidence_insufficiency_repair"] = insufficiency_repaired

        provider_model = str(data.get("model") or self.model).strip()
        return {
            "text": text,
            "provider": f"qwen35-ascend:{provider_model}",
            "error": None,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "usage": usage,
        }

    def _resolved_protocol(self) -> str:
        if self.protocol in {"qwen", "native"}:
            return self.protocol
        return "qwen" if "/api/qwen/generate" in self.endpoint.rstrip("/") else "native"

    def _native_payload(self, question: str, mode: str, contexts: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "prompt": question,
            "mode": mode,
            "context": [self._context_item(item) for item in contexts],
        }

    def _qwen_payload(self, question: str, mode: str, contexts: list[dict[str, Any]]) -> dict[str, Any]:
        evidence = "\n\n".join(
            f"[{index}] {item.get('title', '')}\n来源：{item.get('source', '')}\n{item.get('content', '')}"
            for index, item in enumerate(contexts, start=1)
        )
        system = (
            "你是考研各专业知识库问答智能体。只能依据给定证据回答；证据不足时必须明确说明。"
            "涉及招生人数、分数线、考试科目、参考书、复试或年度政策时，必须提醒用户以对应年份官方通知为准。"
            "回答应清晰、可复核，并在关键结论后标注证据序号，如[1]。"
            "只使用能够直接支撑当前问题的证据，不得为了覆盖全部证据而讨论无关概念；没有使用的证据不要引用。"
            "先给完整结论，再补必要解释；控制在180字以内，不得在句子中途结束。"
            "真题解析必须保留证据中的关键步骤、术语、公式和因果解释。"
            "网址请直接使用纯文本，不要使用 Markdown 超链接格式。"
        )
        mode_instruction = {
            "exam": (
                "按真题解析作答：先定位考点，再逐项写出证据中的关键步骤、报文名、公式或构成要件，"
                "然后解释原理并指出易错点。不得用概括结论代替关键步骤，不得遗漏证据中的关键术语。"
            ),
            "school": (
                "按院校信息核验作答，明确学校、学院、专业和年份边界；必须保留证据中的官方机构全称、"
                "完整官网 URL 和交叉核验入口。"
            ),
            "plan": "按可执行复习计划作答，优先保留与问题直接相关的方法、分类标签和检查动作，再补阶段安排。",
            "qa": "按专业知识问答作答，先回答核心问题；涉及流程时必须保留证据中的参与方、先后顺序和结果。",
        }.get(mode, "按专业知识问答作答。")
        user = (
            f"场景：{mode}\n作答要求：{mode_instruction}\n问题：{question}"
            f"\n\n检索证据：\n{evidence or '无'}"
        )
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": float(os.environ.get("KAOYAN_MODEL_TEMPERATURE", "0")),
            "max_new_tokens": int(os.environ.get("KAOYAN_MODEL_MAX_TOKENS", "768")),
        }

    @staticmethod
    def _context_item(item: dict[str, Any]) -> dict[str, Any]:
        keys = ("id", "title", "source", "source_url", "year", "retrieved_at", "content")
        return {key: item.get(key) for key in keys}

    @staticmethod
    def _extract_text(data: dict[str, Any], protocol: str) -> str:
        if protocol == "qwen":
            return str(data.get("answer") or "").strip()
        return str(data.get("answer") or data.get("text") or data.get("response") or "").strip()

    @staticmethod
    def _coverage_terms(text: str) -> set[str]:
        """Build lightweight terms for checking whether an answer covers evidence."""
        terms: set[str] = set()
        chinese: list[str] = []
        for token in re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]", text.lower()):
            if re.fullmatch(r"[\u4e00-\u9fff]", token):
                chinese.append(token)
                continue
            if chinese:
                terms.update("".join(chinese[index : index + 2]) for index in range(len(chinese) - 1))
                terms.update(chinese)
                chinese = []
            terms.add(token)
        if chinese:
            terms.update("".join(chinese[index : index + 2]) for index in range(len(chinese) - 1))
            terms.update(chinese)
        return {term for term in terms if len(term) >= 2 or re.fullmatch(r"[a-z0-9_]+", term)}

    @classmethod
    def _coverage_gaps(
        cls,
        answer: str,
        question: str,
        mode: str,
        contexts: list[dict[str, Any]],
    ) -> list[str]:
        if not answer or not contexts:
            return []

        if mode == "school":
            return cls._school_coverage_gaps(answer, contexts[0])
        if mode not in {"exam", "qa", "plan"}:
            return []

        answer_terms = cls._coverage_terms(answer)
        top_content = str(contexts[0].get("content") or "")
        clauses = cls._relevant_clauses(question, top_content, mode)
        gaps: list[str] = []
        for clause in clauses:
            facts = cls._missing_facts(clause, question, mode, answer, answer_terms)
            if facts:
                gaps.append("、".join(facts))
        return gaps[:2]

    @classmethod
    def _relevant_clauses(cls, question: str, content: str, mode: str) -> list[str]:
        clauses = [
            clause.strip(" \t\r\n：:，,")
            for clause in re.split(r"[。！？；]+", content)
            if len(clause.strip()) >= 6
        ]
        if not clauses:
            return []

        query_terms = {term for term in cls._coverage_terms(question) if len(term) >= 2}
        scored = [
            (sum(term in cls._coverage_terms(clause) for term in query_terms), index, clause)
            for index, clause in enumerate(clauses)
        ]
        best = max(score for score, _, _ in scored)
        if best <= 0:
            return clauses[:1]

        threshold = max(1, int(best * 0.55))
        selected = [clause for score, _, clause in scored if score >= threshold]
        if mode == "qa":
            return selected[:2]
        return selected[:3]

    @classmethod
    def _missing_facts(
        cls,
        clause: str,
        question: str,
        mode: str,
        answer: str,
        answer_terms: set[str],
    ) -> list[str]:
        facts = cls._enumerated_facts(clause)

        if mode == "exam":
            facts.extend(cls._technical_tokens(clause))
            if any(marker in question for marker in ("为什么", "原因", "原理", "作用", "意义")):
                facts.extend(cls._reason_facts(clause))
        elif mode == "qa" and any(marker in question for marker in ("怎样配合", "如何配合", "解析过程", "工作过程")):
            facts.extend(cls._qualified_terms(clause))
        elif mode == "plan":
            facts.extend(cls._qualified_terms(clause))

        unique: list[str] = []
        for fact in facts:
            fact = fact.strip(" \t\r\n：:，,。；;、")
            if (len(fact) < 2 and fact != "根") or fact in unique:
                continue
            fact_terms = cls._coverage_terms(fact)
            covered = cls._fact_covered(fact, answer) or bool(fact_terms) and all(term in answer_terms for term in fact_terms)
            if not covered:
                unique.append(fact)
        return unique[:4]

    @staticmethod
    def _enumerated_facts(clause: str) -> list[str]:
        facts: list[str] = []
        patterns = (
            r"(?:包括|包含|分别为|分别是|依次为|需要同时满足)([^。；]+)",
            r"按([^。；]+?)分类",
            r"(?:用|通过)([^。；]+?)(?:提取|回顾|复习|自测)",
            r"(?:是否存在|存在)([^。；]+?)(?:等特别事由|特别事由)",
        )
        for pattern in patterns:
            for match in re.finditer(pattern, clause):
                segment = re.split(
                    r"[，,](?=(?:核心|其中|分别|即|它们|二者|前者|后者|主要|通常))",
                    match.group(1),
                    maxsplit=1,
                )[0]
                parts = re.split(r"[、，,]|以及|和|及|或", segment)
                for part in parts:
                    cleaned = re.sub(r"^(?:通常|四个|三个|三种|以下|等)\s*", "", part).strip()
                    cleaned = re.sub(
                        r"(?:[一二三四五六七八九十两]+|\d+)个?"
                        r"(?:必要条件|条件|方面|步骤|要素|机制|方法|原则|维度|阶段|类型|类别)$",
                        "",
                        cleaned,
                    ).strip()
                    if len(cleaned) >= 2:
                        facts.append(cleaned)
        return facts

    @staticmethod
    def _technical_tokens(clause: str) -> list[str]:
        tokens = re.findall(r"\b[A-Z][A-Z0-9]*(?:\+[A-Z0-9]+)?\b", clause)
        return list(dict.fromkeys(token for token in tokens if len(token) >= 2))

    @staticmethod
    def _reason_facts(clause: str) -> list[str]:
        facts: list[str] = []
        for segment in re.split(r"[，,]", clause):
            for marker in ("用于", "说明", "保证", "确保", "减少", "避免", "降低", "提高"):
                if marker not in segment:
                    continue
                fact = segment.split(marker, 1)[1].strip(" ：:")
                if len(fact) >= 4:
                    facts.append(fact)
        return facts

    @staticmethod
    def _qualified_terms(clause: str) -> list[str]:
        terms: list[str] = []
        for match in re.finditer(r"向([^，。；]+)", clause):
            segment = re.split(r"(?:发起|进行|查询|发送|获取)", match.group(1), maxsplit=1)[0]
            for part in re.split(r"、|以及|和|及", segment):
                cleaned = part.strip(" \t\r\n：:，,。；")
                cleaned = re.sub(r"服务器$", "", cleaned).strip()
                if len(cleaned) >= 2 or cleaned == "根":
                    terms.append(cleaned)
        for match in re.finditer(r"([\u4e00-\u9fff]{1,4})\s+([A-Z][A-Za-z0-9]+)", clause):
            prefix = match.group(1)
            for marker in ("本地", "权威", "顶级域"):
                if marker in prefix:
                    prefix = marker
                    break
            terms.append(f"{prefix} {match.group(2)}")
        return terms

    @staticmethod
    def _fact_covered(fact: str, answer: str) -> bool:
        if fact in answer:
            return True
        for prefix in ("犯罪", "基本", "民事"):
            if fact.startswith(prefix) and len(fact) - len(prefix) >= 2:
                if fact[len(prefix) :] in answer:
                    return True
        return False

    @classmethod
    def _school_coverage_gaps(cls, answer: str, context: dict[str, Any]) -> list[str]:
        title = str(context.get("title") or "").strip()
        content = str(context.get("content") or "").strip()
        label = re.sub(r"(?:考研)?官方(?:信息源|入口)$", "", title).strip()
        parts: list[str] = []

        if label and label not in answer:
            parts.append(label)

        urls = cls._official_url_sample(context)
        missing_urls = [url for url in urls if url.rstrip("/") not in answer]
        if missing_urls:
            parts.append("、".join(missing_urls))

        cross_checks = [name for name in ("研究生招生网", "研究生院官网", "研招网院校库") if name in content and name not in answer]
        if cross_checks:
            parts.append("并与" + "、".join(cross_checks) + "交叉核验")

        if not parts:
            return []
        prefix = title or "官方来源"
        return [f"{prefix}：{'；'.join(parts)}"]

    @staticmethod
    def _official_url_sample(context: dict[str, Any]) -> list[str]:
        content = str(context.get("content") or "")
        source_url = str(context.get("source_url") or "").strip()
        urls = re.findall(r"https?://[^\s，。；、）)]+", content)
        ordered = list(dict.fromkeys([source_url, *urls]))
        ordered = [url for url in ordered if url]
        if len(ordered) <= 3:
            return ordered

        selected: list[str] = []

        def add(url: str) -> None:
            if url and url not in selected:
                selected.append(url)

        add(source_url or ordered[0])
        for url in ordered:
            host = urllib.parse.urlparse(url).hostname or ""
            if host.startswith("www.") and host != "www.chsi.com.cn":
                add(url)
                break
        for marker in ("yzb", "yjs", "grad", "gs"):
            match = next(
                (url for url in ordered if marker in (urllib.parse.urlparse(url).hostname or "")),
                "",
            )
            if match:
                add(match)
                break
        for url in ordered:
            if len(selected) >= 3:
                break
            add(url)
        return selected[:3]

    @classmethod
    def _repair_unsupported_admission_count(
        cls,
        question: str,
        mode: str,
        contexts: list[dict[str, Any]],
        answer: str,
    ) -> tuple[str, bool]:
        """Make missing admission-count evidence explicit and auditable."""
        if mode != "school":
            return answer, False

        asks_for_count = re.search(
            r"(?:招收|招生|录取|计划)[^？?。]{0,16}(?:多少|几名|人数)"
            r"|(?:多少|几名)[^？?。]{0,16}(?:硕士|研究生|学生|人)",
            question,
        )
        if not asks_for_count:
            return answer, False

        evidence = "\n".join(
            " ".join(
                str(item.get(key) or "")
                for key in ("title", "source", "content", "year")
            )
            for item in contexts
        )
        number = r"(?:[0-9]{1,5}|[零〇一二两三四五六七八九十百千]{1,8})"
        count_patterns = (
            rf"(?:招生人数|招生计划|计划招收|拟招收|招收)"
            rf"[^。；;\n]{{0,32}}{number}\s*(?:名|人)",
            rf"{number}\s*(?:名|人)[^。；;\n]{{0,20}}"
            rf"(?:硕士研究生|研究生|招生|招收)",
        )
        if any(
            re.search(pattern, evidence, re.IGNORECASE)
            for pattern in count_patterns
        ):
            return answer, False

        normalized_answer = answer.replace(r"\[", "[").replace(r"\]", "]")
        already_explicit = re.search(
            r"(?:现有|当前|给定)?证据[^。！？\n]{0,24}"
            r"(?:未给出|没有|不含|无法支持)[^。！？\n]{0,16}"
            r"(?:招生人数|具体数值|人数)",
            normalized_answer,
        )
        if already_explicit:
            return answer, False

        citations = [int(value) for value in re.findall(r"\[(\d+)\]", normalized_answer)]
        citation = next(
            (value for value in citations if 1 <= value <= len(contexts)),
            1,
        )
        citation_suffix = f"[{citation}]" if contexts else ""
        prefix = (
            "现有证据未给出对应年份的招生人数，"
            f"无法据此确认具体数值{citation_suffix}。"
        )
        return f"{prefix}{answer.lstrip()}", True

    @staticmethod
    def _normalize_links(text: str) -> str:
        """Keep model-produced links readable in terminals and the web UI."""
        text = text.replace(r"\[", "[").replace(r"\]", "]")
        text = re.sub(
            r"\[([^\n]*https?://[^\n]*)\]\(https?://[^)\n]*\)",
            r"\1",
            text,
        )
        text = re.sub(
            r"\[([^\]\n]+)\]\((https?://[^)\n]+)\)",
            r"\1（\2）",
            text,
        )
        text = re.sub(r"\[([^\]\n]*https?://[^\]\n]*)\]", r"\1", text)
        return re.sub(r"\]\((https?://[^)\n]+)\)", r"（\1）", text)

    @staticmethod
    def _deduplicate_sentences(text: str) -> str:
        """Remove exact adjacent sentence repetitions from model output."""
        parts = re.split(r"(?<=[。！？!?])", text)
        kept: list[str] = []
        previous = ""
        for part in parts:
            key = re.sub(r"\s+", " ", part).strip()
            if key and key == previous:
                continue
            kept.append(part)
            if key:
                previous = key
        return "".join(kept).strip()

    @staticmethod
    def _append_grounded_evidence(answer: str, gaps: list[str]) -> str:
        additions = "；".join(gaps)
        if not additions:
            return answer
        return f"{answer.rstrip()}\n证据补充：{additions}。"
