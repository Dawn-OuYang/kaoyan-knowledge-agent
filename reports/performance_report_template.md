# 性能分析报告模板

项目名称：考研各专业知识库问答智能体

状态：待昇腾 NPU 环境实测后回填。当前只记录附件 7 官方样例可提取指标和本项目测试口径。

## 1. 测试环境

| 项目 | 内容 |
| --- | --- |
| 测试日期 | 待填写 |
| 硬件 | 昇腾 NPU 型号、数量、显存 |
| OS | 待填写 |
| CANN | 待填写 |
| Python | 官方建议 Python 3.10 |
| torch / torch_npu | Qwen3VL README 建议 2.7.1 |
| MindSpeed-MM | 附件 7 代码样例 |
| 模型 | Qwen3.5-0.8B |
| 权重格式 | HuggingFace -> DCP |
| 数据集 | `ascend/annotations_slim.json`（当前 192 条）+ 50 条问答评测集 |

## 2. 官方样例基线

附件 7 日志 `qwen35_0.8B_20260608_110844.log` 可提取如下基线，用于说明官方样例已包含性能采集口径，不代表本项目已在本机复测。

| 指标 | 官方样例日志值 |
| --- | --- |
| train_iters | 100 |
| global batch size | 8 |
| iteration 1 step time | 14486.4 ms |
| iteration 100 step time | 11744.3 ms |
| loss 起点 | 12.42247 |
| loss 终点 | 9.068525 |
| after 2 iterations allocated | 12676.57 MB |
| after 2 iterations max allocated | 20056.05 MB |
| after 2 iterations reserved | 22910.0 MB |

## 3. 本项目训练性能

| 配置 | batch | cutoff_len | train_iters | 平均 step time | samples/s | max allocated | loss 起点 | loss 终点 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen3.5-0.8B + 考研 SFT | 8 | 1024 | 100 | 待测 | 待测 | 待测 | 待测 | 待测 |

## 4. 应用推理性能

| 测试项 | 输入长度 | 检索片段数 | 首 token 延迟 | 总响应时间 | tokens/s | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| 专业知识问答 | 待填 | 3 | 待测 | 待测 | 待测 | RAG + Qwen3.5 |
| 真题解析 | 待填 | 3 | 待测 | 待测 | 待测 | Agent 模板 + Qwen3.5 |
| 院校咨询 | 待填 | 3 | 待测 | 待测 | 待测 | 含风险提示 |
| 复习规划 | 待填 | 3 | 待测 | 待测 | 待测 | 含用户画像 |

## 5. 优化记录

| 优化项 | 开关或参数 | 预期影响 | 实测结论 |
| --- | --- | --- | --- |
| recompute | `features.recompute=true` | 降低峰值显存，增加少量计算开销 | 待测 |
| bf16 FSDP | `param_dtype=bf16` | 降低显存压力 | 待测 |
| task queue | `TASK_QUEUE_ENABLE=2` | 优化算子下发 | 待测 |
| memory reuse | `MULTI_STREAM_MEMORY_REUSE=2` | 降低多流内存占用 | 待测 |
| allocator | `PYTORCH_NPU_ALLOC_CONF=expandable_segments:True` | 改善缓存分配 | 待测 |

正式实验使用 `baseline`、`runtime-optimized`、`memory-optimized` 三组同条件对比，原始日志由 `scripts/parse_mindspeed_log.py` 自动解析，汇总由 `scripts/compare_npu_experiments.py` 生成。附件 7 官方样例日志只作为解析口径参考，不进入本项目实测表。

## 6. 结论

待昇腾环境完成正式训练/推理后填写。结论必须包含：功能是否跑通、精度是否达标、性能瓶颈在哪里、采取了哪些优化。
