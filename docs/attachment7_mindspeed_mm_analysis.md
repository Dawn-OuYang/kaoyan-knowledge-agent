# 附件 7 MindSpeed-MM 官方样例分析

读取日期：2026-07-21

附件来源：用户提供的 `赛题参考样例-MindSpeed-MM仓的代码.rar`，已复制到工作区并解压，只读取副本，不改动原始微信文件。

## 1. 附件性质

附件 7 不是普通片段代码，而是一份完整的 `MindSpeed-MM` 仓库样例。它对本项目的影响是：技术路线必须能解释如何从应用层接入 MindSpeed-MM/Qwen3.5，并按官方样例产出训练、精度和性能材料。

## 2. 关键路径

```text
MindSpeed-MM/examples/qwen3_5/
  convert_weight.sh
  finetune_qwen3_5_0.8B.sh
  install_extensions.sh
  qwen3_5_0.8B_config.yaml

MindSpeed-MM/examples/qwen3vl/
  README_v1.md
  convert_weight.sh
  finetune_qwen3vl_v1.sh
  qwen3vl_config_v1.yaml

MindSpeed-MM/checkpoint/vlm_model/converters/qwen3_5.py
MindSpeed-MM/mindspeed_mm/fsdp/models/qwen3_5/
MindSpeed-MM/mindspeed_mm/fsdp/models/qwen3vl/
MindSpeed-MM/logs/qwen35_0.8B_20260608_110844.log
```

## 3. Qwen3.5 官方流程

权重转换：

```bash
python checkpoint/convert_cli.py GenericDCPConverter hf_to_dcp \
  --hf_dir /workspace/mnt/share/weights/Qwen3.5-0.8B \
  --dcp_dir /workspace/mnt/share/weights/Qwen3.5-0.8B-dcp
```

训练启动：

```bash
torchrun ... mindspeed_mm/fsdp/train/trainer.py \
  examples/qwen3_5/qwen3_5_0.8B_config.yaml
```

官方脚本设置的关键环境变量：

```text
NON_MEGATRON=true
MULTI_STREAM_MEMORY_REUSE=2
TASK_QUEUE_ENABLE=2
ASCEND_LAUNCH_BLOCKING=0
ACLNN_CACHE_LIMIT=100000
CPU_AFFINITY_CONF=1
PYTORCH_NPU_ALLOC_CONF=expandable_segments:True
NPUS_PER_NODE=1
```

## 4. Qwen3.5 配置要点

官方 `qwen3_5_0.8B_config.yaml` 中与本项目强相关的字段：

| 字段 | 官方值/含义 | 本项目适配 |
| --- | --- | --- |
| `model_id` | `qwen3_5` | 保持一致 |
| `model_name_or_path` | HF 权重目录 | 昇腾服务器上改为真实 Qwen3.5 路径 |
| `training.load` | DCP 权重目录 | 由 `convert_qwen35_weight.sh` 生成 |
| `dataset_type` | `huggingface` | 使用消息格式 `annotations_slim.json` |
| `dataset` | `annotations_slim.json` | 替换为考研 SFT 数据 |
| `cutoff_len` | `1024` | 初赛样例保持 1024 |
| `template` | `qwen3_vl_nothink` | 保持官方样例 |
| `enable_thinking` | `false` | 保持官方样例，方便可控输出 |
| `micro_batch_size` | `1` | 初始保持官方样例 |
| `gradient_accumulation_steps` | `8` | global batch size 为 8 |
| `train_iters` | `100` | 初赛快速验证先保持 100 |
| `optimizer` | `adamw` | 保持官方样例 |
| `adam_fused` | `true` | 保持官方样例 |
| `recompute` | `true` | 降低显存占用 |

## 5. Qwen3VL 与 COCO 关系

`examples/qwen3vl/README_v1.md` 提到：

- 推荐 Python 3.10。
- 推荐 torch / torch_npu 2.7.1。
- 需要 CANN 和 torch_npu 环境。
- 多模态数据准备以 COCO2017 + LLaVA-Instruct-150K 转换为例。

因此附件 4 的 COCO 数据集可作为多模态验证集。我们的项目主题是考研问答，初赛可先用文本问答数据验证业务能力；若赛题强制多模态验证，则用 COCO 跑通 Qwen3VL 官方验证链路，把考研截图、招生目录图片、真题图片作为扩展方向。

## 6. 官方日志可用指标

附件 7 自带日志 `qwen35_0.8B_20260608_110844.log` 包含：

- `elapsed time per iteration (ms)`
- `global batch size`
- `loss`
- `grad norm`
- memory allocated / max allocated / reserved

可读出的样例值：

| 指标 | 值 |
| --- | --- |
| 训练迭代数 | 100 |
| global batch size | 8 |
| 第 1 步耗时 | 14486.4 ms |
| 第 100 步耗时 | 11744.3 ms |
| loss 起点 | 12.42247 |
| loss 终点 | 9.068525 |
| 2 步后 allocated | 12676.57 MB |
| 2 步后 max allocated | 20056.05 MB |
| 2 步后 reserved | 22910.0 MB |

这些是官方样例日志中的基线，不是本项目在当前机器复测结果。正式报告要用昇腾环境重新跑，并贴本项目日志。

## 7. 对本项目的落地结论

本项目正式技术线确定为：

```text
考研知识库问答 Agent
  -> 考研 SFT/评测数据 annotations_slim.json
  -> Qwen3.5 HF 权重转 DCP
  -> MindSpeed-MM FSDP 训练/适配
  -> 昇腾 NPU 推理/性能验证
  -> 应用层 RAG + Agent 接入模型服务
```

当前本地 MVP 用于演示业务闭环；`ascend/` 目录用于上昇腾服务器后执行官方样例兼容的模型流程；`reports/` 目录用于提交附件要求中的精度日志和性能分析报告。
