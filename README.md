# 考研各专业知识库问答智能体

本项目用于整理和查询考研专业课资料。系统先从本地知识库检索相关内容，再调用 Qwen3.5-0.8B 生成回答，并返回引用来源和时效提示。

目前收录计算机 408、通信工程、法学、复习规划和部分院校信息，支持知识问答、真题解析、复习规划、院校咨询四种模式。招生人数、考试科目、复试安排等信息如果缺少对应年份的依据，系统会直接说明无法确认，不补写未经证实的数据。

## 1. 运行环境

| 项目 | 版本或路径 |
| --- | --- |
| 操作系统 | Ubuntu 22.04.5 LTS |
| 系统架构 | Linux aarch64 |
| Python | 3.11.15 |
| Python 环境 | `/workspace/kaoyan-venv/bin/python` |
| NPU | 2 张 Ascend 910 |
| CANN | 9.0.0 |
| Driver | 25.5.0 |
| Ascend HAL | 7.35.23 |
| PyTorch | 2.10.0+cpu |
| torch_npu | 2.10.0 |
| Transformers | 5.2.0 |
| Accelerate | 1.2.0 |
| Safetensors | 0.8.0 |
| Tokenizers | 0.22.2 |

主要环境变量：

```bash
ASCEND_HOME_PATH=/usr/local/Ascend/cann-9.0.0
ASCEND_TOOLKIT_HOME=/usr/local/Ascend/cann-9.0.0
ASCEND_OPP_PATH=/usr/local/Ascend/cann-9.0.0/opp
ASCEND_AICPU_PATH=/usr/local/Ascend/cann-9.0.0
```

## 2. 模型信息

| 项目 | 内容 |
| --- | --- |
| 模型名称 | Qwen3.5-0.8B-kaoyan-rag-sft-v2-iter80 |
| 模型路径 | `/workspace/kaoyan-lab/models/Qwen3.5-0.8B-kaoyan-rag-sft-v2-iter80` |
| 文件数量 | 7 |
| 总大小 | 3472962572 bytes |

模型目录 Tree SHA-256：

```text
dc2645497d8f05f4571e1af64d46af3640f9f58b034b66db63075716071931ac
```

项目使用 MindSpeed-MM 完成专项微调，共训练 82 个迭代，iter80 的验证 Loss 为 `0.09138869`。主要训练参数如下：

```text
cutoff_len=1024
micro_batch_size=1
gradient_accumulation_steps=4
train_iters=82
save_interval=20
val_interval=20
```

## 3. 启动方式

### 3.1 启动 Qwen3.5 模型服务

```bash
source /workspace/kaoyan-venv/bin/activate

python -u /workspace/kaoyan-lab/kaoyan-knowledge-agent/ascend/qwen35_ascend_server_nothink.py \
  --model-path /workspace/kaoyan-lab/models/Qwen3.5-0.8B-kaoyan-rag-sft-v2-iter80 \
  --model-name Qwen3.5-0.8B-kaoyan-rag-sft-v2-iter80 \
  --host 127.0.0.1 \
  --port 8001
```

检查模型服务：

```bash
curl http://127.0.0.1:8001/health
```

### 3.2 启动 RAG 服务

在另一个终端执行：

```bash
cd /workspace/kaoyan-lab/kaoyan-knowledge-agent/src
source /workspace/kaoyan-venv/bin/activate

export KAOYAN_MODEL_ENDPOINT=http://127.0.0.1:8001/api/qwen/generate
export KAOYAN_MODEL_PROTOCOL=qwen
export KAOYAN_MODEL_NAME=Qwen3.5-0.8B-kaoyan-rag-sft-v2-iter80
export KAOYAN_HOST=127.0.0.1
export KAOYAN_PORT=7863

/workspace/kaoyan-venv/bin/python -u server.py
```

检查 RAG 服务：

```bash
curl http://127.0.0.1:7863/api/health
```

服务启动后访问 `http://127.0.0.1:7863`。

### 3.3 启动最小 Demo

项目根目录提供了 Linux 和 Windows 启动脚本：

```bash
bash run.sh
```

```powershell
.\run.ps1
```

默认访问地址为 `http://127.0.0.1:7860`。该入口可以在不连接微调模型时检查网页、知识库和基础问答流程。

## 4. 代码结构

| 文件或目录 | 作用 |
| --- | --- |
| `src/server.py` | 提供网页和 HTTP 接口 |
| `src/rag_engine.py` | 加载知识库、检索内容并按场景组织回答 |
| `src/model_gateway.py` | 调用 Qwen3.5，处理链接、重复内容和证据不足情况 |
| `static/` | Web 页面、脚本和样式 |
| `data/` | 知识库、来源卡和评测问题 |
| `scripts/` | 数据构建、功能测试、评测和打包脚本 |
| `ascend/` | 权重转换、训练、导出和昇腾推理脚本 |
| `reports/` | 测试报告、审计结果和证据清单 |

一次问答的处理顺序如下：

```text
用户输入问题
  -> server.py 接收请求
  -> 根据专业和模式检索知识库
  -> 过滤不相关内容
  -> 调用 Qwen3.5 模型
  -> 检查引用、链接和证据是否充分
  -> 返回回答、引用、风险提示和耗时
```

主要接口：

```text
GET  /api/health
GET  /api/status
POST /api/ask
POST /api/skill/invoke
```

## 5. 权重转换

HuggingFace 权重转换为 DCP 格式：

```bash
cd /workspace/kaoyan-lab/MindSpeed-MM-torch210
source /workspace/kaoyan-venv/bin/activate

python checkpoint/convert_cli.py GenericDCPConverter hf_to_dcp \
  --hf_dir /workspace/kaoyan-lab/models/Qwen3.5-0.8B \
  --dcp_dir /workspace/kaoyan-lab/models/Qwen3.5-0.8B-dcp
```

## 6. 测试结果

固定 50 条功能回归测试：

```text
测试用例：50
通过：50/50
真实模型调用：50
模型回退：0
引用命中：50/50
安全问题：0
招生人数负向证据约束：2/2
```

重复性能测试使用 20 条固定样例，连续测试 3 轮，共 60 次串行请求：

```text
通过：60/60
平均时延：2684.49 ms
P50 时延：2497.93 ms
P95 时延：4210.26 ms
最大时延：6405.45 ms
平均生成速度：24.372 tokens/s
峰值 NPU 显存：1771.94 MB
```

相关报告：

- `reports/npu_raw/qwen35-rag-sft-v2-quality-v3-3-final-50.json`
- `reports/quality_v3_3_final_50_audit.json`
- `reports/performance_repeat3_quality_v3_3.json`
- `reports/final_evidence_manifest_v3_3.json`

这些数据来自固定样例的工程回归测试，不代表开放领域事实准确率为 100%。性能测试采用单请求串行方式，也不能直接代表并发处理能力。

## 7. PR 链接

本项目 PR：

https://github.com/Dawn-OuYang/kaoyan-knowledge-agent/pull/1

参考工程：

- MindSpeed-MM：https://gitcode.com/Ascend/MindSpeed-MM.git
- MindSpeed：https://gitcode.com/Ascend/MindSpeed.git
- Megatron-LM：https://gitee.com/mirrors/Megatron-LM.git

模型权重不上传至 GitHub，通过复赛交付包单独提供。

## 8. 已知限制

当前知识库主要覆盖计算机 408、通信工程、法学、复习规划和部分示例院校信息，尚未覆盖全部考研专业和院校。

招生人数、考试科目、复试安排、参考书目和分数线等内容会随年份变化。系统只能按照知识库中已有的证据回答，最终应以对应年份的学校官网、研究生院通知和研招网专业目录为准。
