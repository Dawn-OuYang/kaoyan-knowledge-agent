from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "reports" / "npu_raw"
OUT_PATH = ROOT / "reports" / "npu_experiment_comparison.md"


def latest_by_experiment() -> dict[str, dict]:
    results: dict[str, tuple[float, dict]] = {}
    for path in RAW_DIR.glob("*.metrics.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        experiment = data["experiment"]
        modified = path.stat().st_mtime
        if experiment not in results or modified > results[experiment][0]:
            results[experiment] = (modified, data)
    return {key: value[1] for key, value in results.items()}


def improvement(baseline: float, current: float, lower_is_better: bool) -> str:
    if not baseline:
        return "-"
    change = (baseline - current) / baseline if lower_is_better else (current - baseline) / baseline
    return f"{change:+.1%}"


def main() -> None:
    experiments = latest_by_experiment()
    if not experiments:
        raise SystemExit(f"No parsed NPU metrics found under {RAW_DIR}")

    baseline = experiments.get("baseline")
    order = [name for name in ("baseline", "runtime-optimized", "memory-optimized") if name in experiments]
    order.extend(sorted(set(experiments) - set(order)))
    lines = [
        "# 昇腾 NPU 优化实验对比",
        "",
        "| 实验 | 平均 step time (ms) | samples/s | max allocated (MB) | loss 起点 | loss 终点 | step time 改善 | 吞吐改善 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name in order:
        item = experiments[name]
        memory = item.get("memory_mb") or {}
        step_change = improvement(baseline["average_step_time_ms"], item["average_step_time_ms"], True) if baseline else "-"
        throughput_change = improvement(baseline["samples_per_second"], item["samples_per_second"], False) if baseline else "-"
        lines.append(
            f"| {name} | {item['average_step_time_ms']} | {item['samples_per_second']} | "
            f"{memory.get('max_allocated', '未记录')} | {item['loss_start']} | {item['loss_end']} | {step_change} | {throughput_change} |"
        )
    lines.extend(
        [
            "",
            "## 结论填写规则",
            "",
            "- 只有原始日志存在且解析成功的实验才进入本表。",
            "- 基线与优化实验应使用相同模型、数据、batch、迭代数和 NPU 数量。",
            "- 重计算通常以增加 step time 换取显存下降，应同时说明收益和代价。",
        ]
    )
    OUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
