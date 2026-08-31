from __future__ import annotations

import argparse
import json
import re
import statistics
from pathlib import Path


STEP_RE = re.compile(
    r"iteration\s+(?P<iteration>\d+)/\s*(?P<total>\d+).*?"
    r"elapsed time per iteration \(ms\):\s*(?P<step>[\d.]+).*?"
    r"global batch size:\s*(?P<gbs>\d+).*?loss:\s*(?P<loss>[\d.Ee+-]+)"
)
MEMORY_RE = re.compile(
    r"memory \(MB\).*?allocated:\s*(?P<allocated>[\d.]+).*?"
    r"max allocated:\s*(?P<max_allocated>[\d.]+).*?"
    r"reserved:\s*(?P<reserved>[\d.]+).*?max reserved:\s*(?P<max_reserved>[\d.]+)"
)
ENV_RE = re.compile(r"^(?P<key>[A-Za-z0-9_]+)=(?P<value>.*)$", re.MULTILINE)


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse a MindSpeed-MM training log into evidence artifacts.")
    parser.add_argument("log", type=Path)
    parser.add_argument("--warmup-steps", type=int, default=10)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    text = args.log.read_text(encoding="utf-8", errors="replace")
    steps = [
        {
            "iteration": int(match.group("iteration")),
            "total_iterations": int(match.group("total")),
            "step_time_ms": float(match.group("step")),
            "global_batch_size": int(match.group("gbs")),
            "loss": float(match.group("loss")),
        }
        for match in STEP_RE.finditer(text)
    ]
    if not steps:
        raise SystemExit(f"No training iterations found in {args.log}")

    steady = [item for item in steps if item["iteration"] > args.warmup_steps] or steps
    memory_matches = list(MEMORY_RE.finditer(text))
    memory = None
    if memory_matches:
        last = memory_matches[-1]
        memory = {key: float(last.group(key)) for key in ("allocated", "max_allocated", "reserved", "max_reserved")}

    avg_step = statistics.fmean(item["step_time_ms"] for item in steady)
    gbs = steady[0]["global_batch_size"]
    summary = {
        "log_file": args.log.name,
        "experiment": dict(ENV_RE.findall(text)).get("EXPERIMENT_NAME", args.log.stem),
        "iterations_parsed": len(steps),
        "warmup_steps_excluded": args.warmup_steps,
        "average_step_time_ms": round(avg_step, 3),
        "median_step_time_ms": round(statistics.median(item["step_time_ms"] for item in steady), 3),
        "samples_per_second": round(gbs * 1000 / avg_step, 4),
        "global_batch_size": gbs,
        "loss_start": steps[0]["loss"],
        "loss_end": steps[-1]["loss"],
        "loss_change": round(steps[-1]["loss"] - steps[0]["loss"], 6),
        "memory_mb": memory,
        "environment": dict(ENV_RE.findall(text)),
        "steps": steps,
    }

    output_dir = args.output_dir.resolve() if args.output_dir else args.log.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{args.log.stem}.metrics.json"
    md_path = output_dir / f"{args.log.stem}.metrics.md"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                f"# MindSpeed-MM 训练指标：{summary['experiment']}",
                "",
                f"- 日志：`{args.log.name}`",
                f"- 解析迭代数：{summary['iterations_parsed']}",
                f"- 稳态平均 step time：{summary['average_step_time_ms']} ms",
                f"- samples/s：{summary['samples_per_second']}",
                f"- loss：{summary['loss_start']} -> {summary['loss_end']}",
                f"- 最大已分配显存：{memory['max_allocated'] if memory else '日志未记录'} MB",
                f"- 最大保留显存：{memory['max_reserved'] if memory else '日志未记录'} MB",
                "",
                "> 指标由原始 MindSpeed-MM 日志自动解析，原始日志应与本文件一同归档。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({key: value for key, value in summary.items() if key != "steps"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
