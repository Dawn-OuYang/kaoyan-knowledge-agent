from __future__ import annotations

import argparse
import json
import math
import statistics
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, math.ceil(len(ordered) * fraction) - 1))
    return ordered[index]


def post_json(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the live Qwen3.5 Ascend RAG service.")
    parser.add_argument("--endpoint", default="http://127.0.0.1:7860/api/ask")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=240)
    parser.add_argument("--label", default="qwen35-ascend-rag")
    parser.add_argument("--case-ids", nargs="*", default=[], help="Run only the listed evaluation case IDs.")
    args = parser.parse_args()

    cases = json.loads((ROOT / "data" / "eval_questions.json").read_text(encoding="utf-8"))
    extended_path = ROOT / "data" / "eval_questions_extended.json"
    if extended_path.exists():
        cases.extend(json.loads(extended_path.read_text(encoding="utf-8")))
    if args.case_ids:
        by_id = {case["id"]: case for case in cases}
        missing = [case_id for case_id in args.case_ids if case_id not in by_id]
        if missing:
            raise SystemExit(f"Unknown evaluation case IDs: {', '.join(missing)}")
        cases = [by_id[case_id] for case_id in args.case_ids]
    else:
        cases = cases[: args.limit]

    records: list[dict[str, Any]] = []
    started = time.perf_counter()
    for case in cases:
        call_started = time.perf_counter()
        error = None
        try:
            result = post_json(
                args.endpoint,
                {key: case[key] for key in ("question", "specialty", "mode")},
                args.timeout,
            )
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            result = {}
            error = str(exc)

        latency_ms = (time.perf_counter() - call_started) * 1000
        answer = str(result.get("answer") or "")
        citations = result.get("citations") if isinstance(result.get("citations"), list) else []
        citation_titles = [str(item.get("title") or "") for item in citations if isinstance(item, dict)]
        expected_keywords = case.get("expected_keywords", [])
        keyword_hits = [keyword for keyword in expected_keywords if keyword in answer]
        provider = str(result.get("model_provider") or "")
        model_error = result.get("model_error")
        citation_hit = any(case["expected_citation"] in title for title in citation_titles)
        external_model = provider.startswith("qwen35-ascend:") and model_error is None
        keyword_pass = len(keyword_hits) >= max(1, len(expected_keywords) - 1)
        passed = bool(external_model and citation_hit and keyword_pass and answer)
        records.append(
            {
                "case_id": case["id"],
                "question": case["question"],
                "provider": provider,
                "external_model": external_model,
                "model_error": model_error or error,
                "citation_titles": citation_titles,
                "citation_hit": citation_hit,
                "keyword_hits": keyword_hits,
                "expected_keywords": expected_keywords,
                "passed": passed,
                "latency_ms": round(latency_ms, 2),
                "timings": result.get("timings", {}),
                "model_usage": result.get("model_usage", {}),
                "answer": answer,
            }
        )
        print(f"{case['id']}: {'PASS' if passed else 'FAIL'} ({latency_ms:.0f} ms)")

    latencies = [record["latency_ms"] for record in records]
    usage_rows = [record["model_usage"] for record in records if record["model_usage"]]
    summary = {
        "label": args.label,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "endpoint": args.endpoint,
        "case_count": len(records),
        "passed": sum(int(record["passed"]) for record in records),
        "external_model_calls": sum(int(record["external_model"]) for record in records),
        "fallback_count": sum(int(not record["external_model"]) for record in records),
        "citation_hit_count": sum(int(record["citation_hit"]) for record in records),
        "wall_seconds": round(time.perf_counter() - started, 3),
        "latency_ms": {
            "mean": round(statistics.fmean(latencies), 2) if latencies else 0.0,
            "p50": round(percentile(latencies, 0.50), 2),
            "p95": round(percentile(latencies, 0.95), 2),
            "max": round(max(latencies), 2) if latencies else 0.0,
        },
        "completion_tokens_per_second_mean": round(
            statistics.fmean(float(row["completion_tokens_per_second"]) for row in usage_rows if row.get("completion_tokens_per_second") is not None),
            3,
        ) if any(row.get("completion_tokens_per_second") is not None for row in usage_rows) else None,
        "peak_npu_memory_mb_max": round(
            max(float(row["peak_npu_memory_mb"]) for row in usage_rows if row.get("peak_npu_memory_mb") is not None),
            2,
        ) if any(row.get("peak_npu_memory_mb") is not None for row in usage_rows) else None,
        "records": records,
    }

    report_dir = ROOT / "reports" / "npu_raw"
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / f"{args.label}.json"
    md_path = report_dir / f"{args.label}.md"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                f"# Qwen3.5 昇腾 NPU-RAG 实测：{args.label}",
                "",
                f"- 测试时间：{summary['generated_at']}",
                f"- 样例数：{summary['case_count']}",
                f"- 通过：{summary['passed']}/{summary['case_count']}",
                f"- 真实模型调用：{summary['external_model_calls']}",
                f"- 模板回退：{summary['fallback_count']}",
                f"- 引用命中：{summary['citation_hit_count']}/{summary['case_count']}",
                f"- 平均/P50/P95 时延：{summary['latency_ms']['mean']} / {summary['latency_ms']['p50']} / {summary['latency_ms']['p95']} ms",
                f"- 平均生成吞吐：{summary['completion_tokens_per_second_mean']} tokens/s",
                f"- 最大峰值 NPU 显存：{summary['peak_npu_memory_mb_max']} MB",
                "",
                "| 用例 | 真实模型 | 引用命中 | 关键词命中 | 通过 | 时延(ms) |",
                "| --- | --- | --- | --- | --- | --- |",
                *[
                    f"| {row['case_id']} | {'是' if row['external_model'] else '否'} | {'是' if row['citation_hit'] else '否'} | {len(row['keyword_hits'])}/{len(row['expected_keywords'])} | {'是' if row['passed'] else '否'} | {row['latency_ms']} |"
                    for row in records
                ],
                "",
                "> 本报告由在线接口真实调用生成；规则评分用于工程验收，最终精度仍需结合人工事实一致性复核。",
            ]
        ) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({key: value for key, value in summary.items() if key != "records"}, ensure_ascii=False))
    if summary["fallback_count"]:
        raise SystemExit("NPU-RAG evaluation detected model fallback")


if __name__ == "__main__":
    main()
