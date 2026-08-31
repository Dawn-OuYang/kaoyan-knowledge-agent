# 考研各专业知识库问答智能体

面向 2026 C4-AI 昇腾赛道的考研知识库问答 Agent Skill。系统采用“官方来源知识库 + RAG 检索 + 场景 Agent + MindSpeed-MM/Qwen3.5 昇腾适配”技术路线，支持专业知识问答、真题解析、院校咨询、复习规划和引用溯源。

## 当前能力

- 可运行网页 demo、HTTP Skill Runtime 和命令行调用。
- 64 条示例知识条目、192 条 SFT 样本、50 条本地评测问题。
- 院校来源记录 URL、年份、采集日期和时效风险。
- 外部模型网关兼容 Qwen Chat 和项目原生协议。
- 提供昇腾上机预检、配置渲染、权重转换、三组优化实验、日志解析、权重导出和 NPU 推理服务脚本。
- 本地规则回归日志、功能日志和性能基准可自动生成。

当前机器没有昇腾 NPU、CANN、`torch_npu` 和 Qwen3.5 权重，因此真实 NPU 指标仍需在昇腾服务器实测。项目不会把附件 7 官方日志或本地模板性能冒充本项目 NPU 成绩。

## 本地运行

Windows：

```powershell
.\run.ps1
```

Linux/macOS：

```bash
./run.sh
```

浏览器打开 `http://127.0.0.1:7860`。端口冲突时可设置 `KAOYAN_PORT=7861`。

## 本地验证

```powershell
python .\scripts\build_mindspeed_sft_dataset.py
python .\scripts\run_eval.py
python .\scripts\functional_test.py
python .\scripts\benchmark_skill.py --limit 20 --label local-rag-baseline
```

核心输出位于 `reports/rule_regression_log_local.md`、`reports/functional_test_log.md` 和 `ascend/dataset_manifest.json`。其中规则回归不等价于真实模型精度。

## 连接 Qwen3.5 服务

项目支持 Qwen Chat接口：

```powershell
$env:KAOYAN_MODEL_ENDPOINT="http://127.0.0.1:8000/api/qwen/generate"
$env:KAOYAN_MODEL_PROTOCOL="qwen"
$env:KAOYAN_MODEL_NAME="Qwen3.5-0.8B-Kaoyan"
.\run.ps1
```

真实模型基准应强制禁止回退：

```powershell
python .\scripts\benchmark_skill.py --limit 50 --label ascend-qwen35 --require-external-model
```

## 昇腾上机顺序

从 MindSpeed-MM 仓根目录执行：

```bash
bash /path/to/kaoyan-knowledge-agent/ascend/preflight_check.sh
bash /path/to/kaoyan-knowledge-agent/ascend/convert_qwen35_weight.sh
python /path/to/kaoyan-knowledge-agent/ascend/prepare_ascend_run.py \
  --hf-model-dir /workspace/mnt/share/weights/Qwen3.5-0.8B \
  --dcp-model-dir /workspace/mnt/share/weights/Qwen3.5-0.8B-dcp
bash /path/to/kaoyan-knowledge-agent/ascend/run_experiment_matrix.sh
bash /path/to/kaoyan-knowledge-agent/ascend/export_qwen35_weight.sh
python /path/to/kaoyan-knowledge-agent/ascend/qwen35_ascend_server.py \
  --model-path /path/to/kaoyan-knowledge-agent/ascend/runtime/exported_hf
```

完整说明见 `ascend/README.md` 和 `docs/ascend_server_runbook.md`。

## 主要目录

```text
src/           Agent、RAG、HTTP 服务、模型网关
static/        网页演示工作台
data/          知识库、来源元信息、50 条评测问题
scripts/       评测、基准、SFT 数据、日志解析、打包
ascend/        MindSpeed-MM/Qwen3.5 昇腾执行链
docs/          技术路线、附件合规、接口和上机手册
reports/       本地证据、NPU 报告模板和原始日志目录
submissions/   初赛提交材料
```
