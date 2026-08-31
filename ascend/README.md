# 昇腾适配与实验说明

本目录承接附件 7 MindSpeed-MM/Qwen3.5 官方样例，把考研知识库 Skill 接入昇腾 NPU 的训练、推理、精度与性能验证流程。

## 与附件 7 对齐

官方关键流程为：HuggingFace 权重通过 `GenericDCPConverter hf_to_dcp` 转为 DCP，再由 `mindspeed_mm/fsdp/train/trainer.py` 使用 Qwen3.5 YAML 配置训练。本项目保留这条链路，并补充业务数据、实验矩阵、日志解析和 HTTP 推理服务。

## 文件职责

- `annotations_slim.json`：由 64 条知识生成的 192 条 SFT 样本。
- `dataset_manifest.json`：数据规模、专业分布和数据声明。
- `preflight_check.sh`：检查 CANN、NPU、权重、DCP、依赖和训练器。
- `convert_qwen35_weight.sh`：HF -> DCP。
- `prepare_ascend_run.py`：把路径模板渲染为三组可执行 YAML。
- `run_experiment_matrix.sh`：运行基线、运行时优化、显存优化三组实验。
- `finetune_qwen35_kaoyan.sh`：启动 MindSpeed-MM 训练并解析日志。
- `export_qwen35_weight.sh`：DCP -> HF，供推理服务加载。
- `qwen35_ascend_server.py`：在 Ascend NPU 上提供 Qwen Chat 接口。
- `start_qwen35_rag.sh`：启动 Qwen3.5 昇腾推理服务和考研 RAG 服务，并执行健康检查。

## 实验矩阵

| 实验 | task queue | memory reuse | CPU affinity | recompute | 目的 |
| --- | --- | --- | --- | --- | --- |
| baseline | 0 | 0 | 0 | false | 原始基线 |
| runtime-optimized | 2 | 2 | 1 | false | 比较 step time 与吞吐 |
| memory-optimized | 2 | 2 | 1 | true | 比较峰值显存及速度代价 |

三组实验必须保持模型、数据、batch、迭代数和 NPU 数量一致。解析结果写入 `reports/npu_raw/`，汇总写入 `reports/npu_experiment_comparison.md`。

## 真实 Skill 接入

导出微调权重并启动推理服务后，在应用进程设置：

```bash
export KAOYAN_MODEL_ENDPOINT=http://127.0.0.1:8000/api/qwen/generate
export KAOYAN_MODEL_PROTOCOL=qwen
export KAOYAN_MODEL_NAME=Qwen3.5-0.8B-Kaoyan
python src/server.py
```

随后使用 `scripts/benchmark_skill.py --require-external-model` 生成真实模型基准，任何回退都会使命令失败。

## 真实性边界

当前仓库中的 `reports/official_sample_evidence/` 只证明日志解析器能读取附件 7 官方样例，不代表本项目实测。只有在项目 NPU 环境产生并归档到 `reports/npu_raw/` 的原始日志，才能用于正式性能报告。
