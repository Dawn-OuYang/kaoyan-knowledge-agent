from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_engine import KaoyanAgent, KnowledgeBase


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(len(ordered) * fraction) - 1))
    return ordered[index]


def load_cases(limit: int) -> list[dict]:
    paths = [ROOT / "data" / "eval_questions.json", ROOT / "data" / "eval_questions_extended.json"]
    cases = []
    for path in paths:
        if path.exists():
            cases.extend(json.loads(path.read_text(encoding="utf-8")))
    return cases[:limit]


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark local RAG or a connected Qwen3.5 endpoint.")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--require-external-model", action="store_true")
    parser.add_argument("--label", default="local-template")
    args = parser.parse_args()

    agent = KaoyanAgent(KnowledgeBase(ROOT / "data" / "knowledge_base.json"))
    cases = load_cases(args.limit)
    if not cases:
        raise SystemExit("No benchmark cases found")

    for case in cases[: args.warmup]:
        agent.answer(case["question"], specialty=case["specialty"], mode=case["mode"])

    records = []
    fallback_count = 0
    started = time.perf_counter()
    for _ in range(args.repeat):
        for case in cases:
            result = agent.answer(case["question"], specialty=case["specialty"], mode=case["mode"])
            provider = result["model_provider"]
            fallback_count += int(provider == "local-template")
            records.append(
                {
                    "case_id": case["id"],
                    "mode": case["mode"],
                    "provider": provider,
                    **result["timings"],
                    "prompt_tokens": result.get("model_usage", {}).get("prompt_tokens"),
                    "completion_tokens": result.get("model_usage", {}).get("completion_tokens"),
                }
            )
    wall_seconds = time.perf_counter() - started

    if args.require_external_model and fallback_count:
        raise SystemExit(f"External model was required, but {fallback_count}/{len(records)} calls used fallback")

    totals = [record["total_ms"] for record in records]
    retrievals = [record["retrieval_ms"] for record in records]
    generations = [record["generation_ms"] for record in records]
    completion_tokens = sum(int(record["completion_tokens"] or 0) for record in records)
    summary = {
        "label": args.label,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "case_count": len(records),
        "unique_cases": len(cases),
        "repeat": args.repeat,
        "providers": sorted({record["provider"] for record in records}),
        "fallback_count": fallback_count,
        "wall_seconds": round(wall_seconds, 3),
        "requests_per_second": round(len(records) / wall_seconds, 3) if wall_seconds else 0.0,
        "latency_ms": {
            "mean": round(statistics.fmean(totals), 2),
            "p50": round(percentile(totals, 0.50), 2),
            "p95": round(percentile(totals, 0.95), 2),
            "max": round(max(totals), 2),
        },
        "retrieval_ms_mean": round(statistics.fmean(retrievals), 2),
        "generation_ms_mean": round(statistics.fmean(generations), 2),
        "completion_tokens": completion_tokens,
        "completion_tokens_per_second": round(completion_tokens / wall_seconds, 3) if completion_tokens else None,
        "records": records,
    }

    report_dir = ROOT / "reports" / "benchmarks"
    report_dir.mkdir(parents=True, exist_ok=True)
    safe_label = "".join(char if char.isalnum() or char in "-_" else "-" for char in args.label)
    json_path = report_dir / f"{safe_label}.json"
    md_path = report_dir / f"{safe_label}.md"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                f"# Skill 性能基准：{args.label}",
                "",
                f"- 测试时间：{summary['generated_at']}",
                f"- 调用次数：{summary['case_count']}",
                f"- 模型提供方：{'、'.join(summary['providers'])}",
                f"- 回退到本地模板：{summary['fallback_count']} 次",
                f"- 平均总时延：{summary['latency_ms']['mean']} ms",
                f"- P50/P95：{summary['latency_ms']['p50']} / {summary['latency_ms']['p95']} ms",
                f"- 平均检索时延：{summary['retrieval_ms_mean']} ms",
                f"- 平均生成时延：{summary['generation_ms_mean']} ms",
                f"- 吞吐：{summary['requests_per_second']} requests/s",
                f"- 生成 token 吞吐：{summary['completion_tokens_per_second'] or '服务未返回 usage，无法计算'}",
                "",
                "> 本报告只代表所标注运行环境；本地模板结果不能代替昇腾 NPU/Qwen3.5 实测。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({key: value for key, value in summary.items() if key != "records"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
