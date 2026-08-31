# 昇腾 NPU 证据归档清单

| 证据 | 必需 | 目标位置 | 状态 |
| --- | --- | --- | --- |
| `npu-smi info` 与软件版本 | 是 | `reports/npu_raw/environment.txt` | 待上机 |
| HF -> DCP 转换日志 | 是 | `reports/npu_raw/convert.log` | 待上机 |
| 三组训练原始日志 | 是 | `reports/npu_raw/*.log` | 待上机 |
| 自动解析指标 JSON/MD | 是 | `reports/npu_raw/*.metrics.*` | 待上机 |
| profiling 原始目录 | 是 | `ascend/runtime/*/profiling/` | 待上机 |
| memory snapshot | 建议 | `ascend/runtime/*/memory_snapshot/` | 待上机 |
| 优化实验对比表 | 是 | `reports/npu_experiment_comparison.md` | 待上机 |
| 导出 HF 权重目录清单 | 是 | `reports/npu_raw/export_manifest.txt` | 待上机 |
| Qwen3.5 推理 health 响应 | 是 | `reports/npu_raw/inference_health.json` | 待上机 |
| 外部模型 Skill 基准 | 是 | `reports/benchmarks/ascend-qwen35.*` | 待上机 |
| 50 条真实模型精度日志 | 是 | `reports/accuracy_log_ascend_qwen35.md` | 待上机 |

附件 7 官方日志解析结果保存在 `reports/official_sample_evidence/`，只能作为工具验证和官方口径参考，不计入本项目成绩。
