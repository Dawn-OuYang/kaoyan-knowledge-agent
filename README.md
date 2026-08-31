README：镜像环境、运行脚本与代码逻辑
一、环境版本
运行环境	Linux aarch64
操作系统	Ubuntu 22.04.5 LTS
Python 版本	3.11.15
Python 环境路径	/workspace/kaoyan-venv/bin/python
NPU	2 张 Ascend 910
模型名称	Qwen3.5-0.8B-kaoyan-rag-sft-v2-iter80
模型路径	/workspace/kaoyan-lab/models/Qwen3.5-0.8B-kaoyan-rag-sft-v2-iter80
模型目录包含 7 个文件，总大小为 3472962572 bytes。
模型目录 Tree SHA-256：
dc2645497d8f05f4571e1af64d46af3640f9f58b034b66db63075716071931ac
二、CANN 版本
CANN 版本：9.0.0
Driver 版本：25.5.0
Ascend HAL 版本：7.35.23
主要环境变量如下：
ASCEND_HOME_PATH=/usr/local/Ascend/cann-9.0.0
ASCEND_TOOLKIT_HOME=/usr/local/Ascend/cann-9.0.0
ASCEND_OPP_PATH=/usr/local/Ascend/cann-9.0.0/opp
ASCEND_AICPU_PATH=/usr/local/Ascend/cann-9.0.0

三、torch_npu 版本
PyTorch 版本：2.10.0+cpu
torch_npu 版本：2.10.0
Transformers 版本：5.2.0
Accelerate 版本：1.2.0
Safetensors 版本：0.8.0
Tokenizers 版本：0.22.2

项目通过 torch_npu 调用 Ascend NPU 完成 Qwen3.5-0.8B 模型推理。模型服务健康检查返回设备为 Ascend NPU。
四、运行启动脚本
1. 启动 Qwen3.5 模型服务
source /workspace/kaoyan-venv/bin/activate
python -u /workspace/kaoyan-lab/kaoyan-knowledge-agent/ascend/qwen35_ascend_server_nothink.py \
  --model-path /workspace/kaoyan-lab/models/Qwen3.5-0.8B-kaoyan-rag-sft-v2-iter80 \
  --model-name Qwen3.5-0.8B-kaoyan-rag-sft-v2-iter80 \
  --host 127.0.0.1 \
  --port 8001
模型服务检查：
curl http://127.0.0.1:8001/health
2. 启动考研知识库 RAG 服务
cd /workspace/kaoyan-lab/kaoyan-knowledge-agent/src
source /workspace/kaoyan-venv/bin/activate
export KAOYAN_MODEL_ENDPOINT=http://127.0.0.1:8001/api/qwen/generate
export KAOYAN_MODEL_PROTOCOL=qwen
export KAOYAN_MODEL_NAME=Qwen3.5-0.8B-kaoyan-rag-sft-v2-iter80
export KAOYAN_HOST=127.0.0.1
export KAOYAN_PORT=7863

/workspace/kaoyan-venv/bin/python -u server.py

RAG 服务检查：

curl http://127.0.0.1:7863/api/health

3. 启动最小 Demo
在项目根目录执行：
bash run.sh
Windows 环境执行：
.\run.ps1
默认网页地址：
http://127.0.0.1:7860
昇腾实测时使用的服务地址为：
http://127.0.0.1:7863


五、代码结构说明
项目主要由应用层、知识库检索层、模型调用层和昇腾推理层组成。

src/server.py：
负责提供 HTTP 服务和网页访问入口，接收用户的 question、specialty、mode 和 profile 参数，并提供 /api/ask、/api/health、/api/status 以及 /api/skill/invoke 接口。

src/rag_engine.py：
负责知识库加载、文本分词、相关性检索、专业过滤和场景路由。系统支持知识问答、真题解析、院校咨询和复习规划四种模式。

src/model_gateway.py：
负责连接 Qwen3.5 模型服务，组装模型请求，解析模型返回结果，并执行链接规范化、重复句处理和证据不足保护。

ascend/qwen35_ascend_server_nothink.py：
负责在 Ascend NPU 上加载 Qwen3.5-0.8B 微调模型，并通过 HTTP 接口提供模型生成服务。

data/：
保存基础知识库、扩展知识库、来源卡、评测问题和项目数据。

static/：
保存 Web Demo 的网页、脚本和样式文件。

scripts/：
保存功能测试、固定回归、NPU-RAG 评测、性能测试、数据构建和打包脚本。

ascend/：
保存 Qwen3.5 权重转换、MindSpeed-MM 训练配置、模型导出、NPU 推理和启动脚本。

reports/：
保存精度评测、性能测试、审计结果、原始日志和最终证据清单。

系统执行流程如下：
用户输入问题后，server.py 接收请求；KaoyanAgent 根据问题判断专业和使用场景；KnowledgeBase 检索相关知识并进行专业过滤；模型网关将问题和检索证据发送给 Qwen3.5；系统对模型输出进行引用、链接、重复内容和证据充分性检查；最终返回回答、引用来源、置信度、风险提示和耗时信息。
当用户询问招生人数、考试科目或复试安排等时效性内容时，系统会检查现有证据是否包含对应年份和具体信息。如果证据不足，系统会明确提示无法确认，不生成没有依据的具体数字。

六、PR 链接
参考工程仓库：

MindSpeed-MM：
https://gitcode.com/Ascend/MindSpeed-MM.git

MindSpeed：
https://gitcode.com/Ascend/MindSpeed.git

Megatron-LM：
https://gitee.com/mirrors/Megatron-LM.git

本项目 PR 链接：

https://github.com/Dawn-OuYang/kaoyan-knowledge-agent/pull/1

七、测试结果与已知限制
1 测试结果
项目已在 Ascend NPU 环境完成 Qwen3.5-0.8B 微调模型的推理验证。
最终固定 50 条功能回归测试全部通过，测试结果如下：
测试用例数量：50
通过数量：50/50
真实模型调用：50 次
模型回退次数：0
引用命中：50/50
安全问题：0
招生人数负向证据约束测试：2/2
重复性能测试采用 20 条固定样例，连续测试 3 轮，共完成 60 次单请求串行调用，测试结果如下：
测试请求数量：60
通过数量：60/60
平均时延：2684.49 ms
P50 时延：2497.93 ms
P95 时延：4210.26 ms
最大时延：6405.45 ms
平均生成速度：24.372 tokens/s
峰值 NPU 显存：1771.94 MB
相关测试报告和审计文件包括：
reports/npu_raw/qwen35-rag-sft-v2-quality-v3-3-final-50.json
reports/quality_v3_3_final_50_audit.json
reports/performance_repeat3_quality_v3_3.json
reports/final_evidence_manifest_v3_3.json
2 已知限制
上述 50/50 和 60/60 结果属于固定测试样例下的工程回归结果，用于验证系统功能、模型调用、引用返回和异常保护机制，不等同于开放领域事实准确率 100%。
性能测试采用单请求串行方式完成，测试结果主要反映当前模型、知识库和推理服务配置下的响应情况，不能直接代表系统在高并发条件下的处理能力。
当前知识库主要覆盖计算机 408、通信工程、法学、复习规划以及部分示例院校信息。知识库范围以交付包中的实际数据为准，后续还需要持续补充更多专业、院校和年份资料。
招生人数、考试科目、复试安排、参考书目和分数线等信息具有较强的时效性。系统只根据当前检索到的证据进行回答；如果现有证据不包含对应年份的具体信息，系统会提示无法确认，用户仍需以对应年份学校官网、研究生院通知和研招网专业目录为准。
本项目的 Web 服务、RAG 服务和模型推理服务需要按照运行说明正确启动，并在具备相应依赖和 Ascend NPU 的环境中运行。模型文件、Python 环境、CANN、torch-npu 版本和服务端口发生变化时，需要根据实际环境调整启动命令。。
