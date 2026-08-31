# 昇腾服务器上机手册

## 1. 前置条件

- 昇腾 NPU 可用，`npu-smi info` 正常。
- CANN 环境脚本存在。
- Python 3.10、torch 2.7.1、torch_npu 2.7.1、transformers 4.57.0 与附件 7 MindSpeed-MM 环境一致。
- Qwen3.5-0.8B HuggingFace 权重合法可用。

## 2. 构建数据

```bash
python scripts/build_mindspeed_sft_dataset.py
```

核对 `ascend/dataset_manifest.json`：64 条知识、192 条 SFT 样本。真实扩容后数字会自动更新。

## 3. 预检与权重转换

在 MindSpeed-MM 仓根目录：

```bash
export HF_DIR=/workspace/mnt/share/weights/Qwen3.5-0.8B
export DCP_DIR=/workspace/mnt/share/weights/Qwen3.5-0.8B-dcp
bash /project/kaoyan-knowledge-agent/ascend/preflight_check.sh
bash /project/kaoyan-knowledge-agent/ascend/convert_qwen35_weight.sh
```

## 4. 渲染配置并训练

```bash
python /project/kaoyan-knowledge-agent/ascend/prepare_ascend_run.py \
  --hf-model-dir "$HF_DIR" \
  --dcp-model-dir "$DCP_DIR"
bash /project/kaoyan-knowledge-agent/ascend/run_experiment_matrix.sh
```

必须归档 `reports/npu_raw/*.log`、`*.metrics.json`、profiling 和 memory snapshot。三组实验完成后检查 `reports/npu_experiment_comparison.md`。

## 5. 导出与启动推理

```bash
export LOAD_DIR=/project/kaoyan-knowledge-agent/ascend/runtime/runtime-optimized/checkpoints/release
export SAVE_DIR=/project/kaoyan-knowledge-agent/ascend/runtime/exported_hf
bash /project/kaoyan-knowledge-agent/ascend/export_qwen35_weight.sh
python /project/kaoyan-knowledge-agent/ascend/qwen35_ascend_server.py \
  --model-path "$SAVE_DIR" --host 127.0.0.1 --port 8000
```

另一个终端检查：

```bash
curl http://127.0.0.1:8000/health
```

## 6. 连接 Skill 并正式评测

```bash
export KAOYAN_MODEL_ENDPOINT=http://127.0.0.1:8000/api/qwen/generate
export KAOYAN_MODEL_PROTOCOL=qwen
export KAOYAN_MODEL_NAME=Qwen3.5-0.8B-Kaoyan
python src/server.py
python scripts/benchmark_skill.py --limit 50 --label ascend-qwen35 --require-external-model
python scripts/run_eval.py
```

注意：当前 `run_eval.py` 的自动关键词评分适合回归测试，正式复赛还应增加人工盲评、事实一致性和拒答评测。

## 7. 报告回填

从真实日志回填：环境版本、NPU 型号/数量、step time、samples/s、峰值显存、loss、总响应时延、token 吞吐、优化前后对比。任何空缺项写“未测”，不使用附件 7 官方样例值代替。
