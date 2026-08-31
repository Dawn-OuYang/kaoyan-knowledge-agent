# 初赛源码包逐文件说明

说明对象：`dist/kaoyan-knowledge-agent-initial-round.zip`

核对日期：2026-07-23

该压缩包共有 71 个文件。本说明以压缩包中的实际内容为准，帮助非技术成员理解每个文件是什么、由谁使用、当前是否已经真正生效。

## 一、先理解整个项目

项目可以分成五层：

```text
用户网页
  -> HTTP 服务
  -> RAG 检索与四类 Agent
  -> 本地回答模板或外部 Qwen3.5
  -> 带引用、风险提示和耗时的回答

知识数据与评测集
  -> 生成 SFT 数据
  -> MindSpeed-MM/Qwen3.5 昇腾训练
  -> 导出模型并启动 NPU 推理服务
  -> 重新接入上面的 HTTP Skill
```

各目录的角色：

| 目录 | 通俗理解 | 当前状态 |
| --- | --- | --- |
| `src/` | 项目的大脑和服务端 | 本地已运行 |
| `static/` | 用户看到的网页 | 本地已运行 |
| `data/` | 知识、学校来源和测试题 | 本地已使用 |
| `scripts/` | 测试、生成数据、打包的工具箱 | 本地大部分已运行 |
| `ascend/` | 在昇腾 NPU 上训练和部署 Qwen3.5 的执行链 | 已准备，真实 NPU 待实跑 |
| `reports/` | 测试结果、证据和报告模板 | 本地证据已生成，NPU 证据待补 |
| `docs/` | 技术路线、比赛要求和答辩说明 | 已完成阶段性文档 |
| `submissions/` | 初赛正式上传材料 | 文件已生成，报名信息和签名待补 |

## 二、本地 Demo 是怎样工作的

1. 用户执行 `run.ps1` 或 `run.sh`。
2. 启动 `src/server.py`，默认监听 `127.0.0.1:7860`。
3. 服务启动时，`src/rag_engine.py` 读取 `knowledge_base.json` 和 `knowledge_expansion.json`，再用 `source_cards_sample.json` 补充来源、年份和链接。
4. 浏览器加载 `static/index.html`、`static/styles.css` 和 `static/app.js`。
5. 用户选择专业和 Agent 模式，网页向 `/api/ask` 发送问题。
6. `KaoyanAgent` 根据模式进入知识问答、真题解析、院校咨询或复习规划流程。
7. 知识库用中文字符、中文二元词组和英文词进行 BM25 风格的相关性检索。
8. `model_gateway.py` 检查是否配置了外部模型地址：没有则使用本地模板；有则把检索证据发送给 Qwen3.5 服务。
9. 服务返回答案、引用、置信度、时效风险提示、模型身份和分阶段耗时。

因此，当前本地 Demo 真正跑通的是“网页 + RAG + Agent + 引用”；默认答案生成器是规则模板，不是本机上的 Qwen3.5。

## 三、根目录文件，共 3 个

### `README.md`

项目总入口说明。介绍作品定位、当前能力、本地启动命令、测试命令、外部 Qwen3.5 接入方式、昇腾上机顺序和目录结构。评委或技术人员解压后应先阅读它。

### `run.ps1`

Windows 一键启动脚本。它会切换到项目根目录，依次寻找标准 `python` 或 `py -3` 命令，找到后执行 `src/server.py`；运行环境应预先安装 Python 3.10 及以上版本。

### `run.sh`

Linux、macOS 和昇腾服务器上的本地应用启动脚本。优先调用 `python3`，其次调用 `python`，最后执行 `src/server.py`。它只启动应用服务，不会自动训练 Qwen3.5。

## 四、`src/` 核心程序，共 3 个

### `src/rag_engine.py`

项目最核心的业务文件，相当于“大脑”。主要包含：

- `Document`：定义一条知识应包含的专业、科目、标题、正文、来源、学校、年份和风险等级等字段。
- `KnowledgeBase`：合并基础知识和扩展知识，用来源卡片补充元数据，去重后形成 64 条运行时知识。
- `tokenize`：把中文拆成单字和相邻二元词组，同时保留英文和数字，用于检索。
- `search`：实现 BM25 风格的关键词相关性打分，并按专业方向过滤和加权。
- `KaoyanAgent`：根据 `qa`、`exam`、`school`、`plan` 路由到四类 Agent。
- 回答结构：生成知识摘要、真题作答结构、院校核验提示或三阶段复习计划。
- 可靠性控制：计算检索置信度，对“今年、最新、分数线、招生人数、参考书、复试”触发时效提醒。
- `invoke_skill`：把普通回答封装成正式 Skill 返回结构。

修改这个文件会直接改变检索排序、回答结构、风险提示和 Skill 输出格式。

### `src/model_gateway.py`

模型连接器。它把业务 Agent 与真正的 Qwen3.5 推理服务解耦：

- 从 `KAOYAN_MODEL_ENDPOINT` 读取模型接口地址。
- 支持项目自定义的 Qwen Chat `/api/qwen/generate` 协议和通用原生协议。
- 把问题、场景和前三条检索证据组合成提示词。
- 要求模型只依据证据回答，并对年度招生信息提示官方核验。
- 模型无法访问或返回空内容时，自动退回 `rag_engine.py` 生成的本地模板答案。
- 返回模型名称、调用耗时、token 使用量和错误信息。

未设置 `KAOYAN_MODEL_ENDPOINT` 时，它不会调用 Qwen3.5，状态会明确显示 `local-template`。

### `src/server.py`

项目 HTTP 服务器和网页服务器。使用 Python 标准库 `ThreadingHTTPServer`，不依赖 Flask。

主要接口：

- `GET /`：返回演示网页。
- `GET /api/health`：检查服务和模型网关状态。
- `GET /api/status`：返回 Skill 版本、知识条数、专业列表和模型状态。
- `GET /api/specialties`：返回网页专业下拉列表。
- `POST /api/ask`：供网页调用，返回 Agent 回答。
- `POST /api/skill/invoke`：标准化 Skill 调用入口。

它还负责安全地读取静态文件、解析 JSON 请求和返回 UTF-8 JSON。

## 五、`static/` 网页，共 3 个

### `static/index.html`

网页骨架。定义左侧专业选择、四种模式按钮、知识库和模型状态，以及右侧对话区、问题输入框和复习规划补充字段。它只负责页面结构，不负责回答问题。

### `static/app.js`

网页交互逻辑。启动时读取专业列表和服务状态；处理模式切换、示例问题、表单提交；调用 `/api/ask`；把答案、引用、置信度、模型身份、风险提示和耗时渲染到页面。输出内容会先做 HTML 转义，降低把回答当成网页代码执行的风险。

### `static/styles.css`

网页视觉样式。负责布局、颜色、按钮、对话气泡、引用列表、警告提示和响应式显示。修改它只改变外观，不改变检索或答案内容。

## 六、`data/` 数据文件，共 8 个

### `data/knowledge_base.json`

基础知识库，共 27 条。包含计算机 408、通信工程、法学、通用规划和院校信息的首批样例。每条至少有 `id`、专业、科目、标题、来源和正文。它是运行时直接读取的数据。

### `data/knowledge_expansion.json`

扩展知识库，共 37 条。补充更多专业知识点、院校入口和通用规则。服务启动时自动和基础知识库合并，因此运行时共有 64 条知识。新增稳定知识时可以写入这里，但必须保持唯一 `id` 和统一字段。

### `data/source_cards_sample.json`

来源元数据卡片，共 14 条。为相同 `id` 的知识补充官方链接、学校、专业、年份、发布日期、采集日期和时效风险。运行时主要把它当作“元数据覆盖层”，不是独立的全文数据库。

### `data/source_registry.json`

数据源登记表，共 6 个研招网来源，包括首页、院校库、招生简章、专业库、硕士目录和网报公告。记录每个来源适合回答什么、更新频率和采集注意事项。当前不被问答服务直接加载，主要用于数据治理和答辩说明。

### `data/project_scope.json`

项目示范范围定义。记录三个专业方向的科目范围，以及沈阳工业大学、北京理工大学、上海交通大学、清华大学及相关学院官网。它用于统一项目边界和后续数据扩展，不被当前检索引擎直接读取。

### `data/eval_questions.json`

基础规则评测集，共 20 题。每题记录模式、专业、问题、期望引用和期望关键词，供 `run_eval.py` 和 `benchmark_skill.py` 使用。

### `data/eval_questions_extended.json`

扩展规则评测集，共 30 题。与前 20 题合并后形成 50 题本地测试。作用是扩大四类场景覆盖，但仍是固定规则回归，不等于大模型真实精度。

### `data/sample_skill_request.json`

一个标准 Skill 请求示例。内容是“今年清华大学计算机专业招生人数是多少”，模式为院校咨询。可配合 `skill_cli.py --input-json` 演示结构化调用。

## 七、`scripts/` 工具脚本，共 13 个

### `scripts/functional_test.py`

四项核心功能冒烟测试，分别检查知识问答、真题解析、院校时效提示和复习规划。要求有引用并包含关键内容，结果写入 `reports/functional_test_log.md`。它验证基本功能没有坏，不验证答案的广泛真实性。

### `scripts/run_eval.py`

读取 20+30 道评测题，按关键词覆盖、引用命中、Agent 路由、风险提示和回答长度进行 10 分制规则评分，生成 `reports/rule_regression_log_local.md`。这是工程回归工具，不是 Qwen3.5 模型精度评测。

### `scripts/benchmark_skill.py`

性能基准工具。重复调用 Agent，统计平均时延、P50、P95、检索时延、生成时延、请求吞吐和 token 吞吐。`--require-external-model` 会在任何请求退回本地模板时直接失败，用于保证正式 NPU 基准确实调用了外部模型。

### `scripts/skill_cli.py`

命令行版 Skill 调用器。不打开网页也能提问，可直接传问题和模式，也可读取 JSON 请求文件，并把完整 Skill 结果打印或写入 JSON。它直接加载本地 Agent，不经过 `server.py` 的 HTTP 接口。

### `scripts/mock_qwen_server.py`

Qwen Chat 测试替身，只返回固定的“外部模型链路测试成功”文字。用于验证 `model_gateway.py` 的网络协议、返回解析和模型身份标记，不能当作真实 Qwen3.5 推理结果。

### `scripts/build_mindspeed_sft_dataset.py`

训练数据生成器。读取 64 条知识，为每条自动生成 3 种用户问法和对应答案，输出 192 条 MindSpeed-MM 格式 SFT 样本到 `ascend/annotations_slim.json`，并生成数据清单。修改知识库后应重新运行它。

### `scripts/import_source_cards.py`

把 `source_cards_sample.json` 中尚未存在于基础知识库的卡片追加到 `knowledge_base.json`。它会修改原始数据文件，运行前需要确认不会造成不希望的重复或数据结构变化。

### `scripts/parse_mindspeed_log.py`

MindSpeed-MM 训练日志解析器。从真实日志中提取迭代次数、step time、global batch size、loss、显存和环境变量，计算平均时延与 samples/s，并生成 JSON 和 Markdown 指标文件。

### `scripts/compare_npu_experiments.py`

读取 `reports/npu_raw/` 中三组真实实验指标，比较基线、运行时优化和显存优化的 step time、吞吐、显存与 loss，生成正式对比表。没有真实日志时会拒绝生成结果。

### `scripts/build_initial_creative_book_docx.py`

把 Markdown 创意书组装成附件 1 结构的 Word 文档，包括封面、团队表、原创声明、正文和 Demo 说明。脚本中仍使用报名信息占位符，填写团队信息后需要同步调整生成逻辑或人工编辑最终文档。

### `scripts/build_initial_creative_book_pdf.py`

使用 ReportLab 直接生成 A4 PDF，保证在没有 Word/LibreOffice 时也能得到稳定版式。它依赖 Windows 的宋体文件路径，并同样包含报名信息占位符，所以不是跨系统通用生成器。

### `scripts/validate_initial_submission.py`

初赛提交自检工具。检查创意书字符数、DOCX/PDF 是否存在、PDF 页数、ZIP 必需目录和嵌套压缩包，并把结果写入 `reports/initial_submission_validation.md`。它能提示占位符和签名，但不能代替人工核对真实报名信息。

### `scripts/package_initial_submission.py`

源码打包工具。收集根目录、八个主要目录和初赛材料，排除缓存、临时 NPU 目录及 ZIP/RAR/7z，生成 `dist/kaoyan-knowledge-agent-initial-round.zip`，并再次检查压缩包内没有套娃归档。

## 八、`ascend/` 昇腾执行链，共 11 个

### `ascend/README.md`

昇腾目录总说明。解释它如何对齐附件 7、各脚本职责、三组实验差异、真实 Skill 接入方式以及哪些指标不能冒充项目实测。

### `ascend/annotations_slim.json`

由 64 条知识自动生成的 192 条 SFT 训练样本。每条包含空图片列表、用户/助手消息和专业、科目、知识编号等元数据。它是训练输入，不是运行时检索知识库。

### `ascend/dataset_manifest.json`

训练数据清单。记录生成日期、64 条知识、192 条样本、每条知识生成 3 个样本、专业分布、来源类型和数据声明，便于复现实验与避免夸大数据规模。

### `ascend/qwen3_5_kaoyan_config.yaml`

MindSpeed-MM Qwen3.5 训练配置模板。设置 FSDP、bf16、数据字段、最大长度、batch、学习率、训练 100 次、重计算、profiling、DCP 加载和保存目录。文件中的 `__HF_MODEL_DIR__` 等占位符不能直接训练，必须先由 `prepare_ascend_run.py` 渲染。

### `ascend/preflight_check.sh`

昇腾服务器环境预检。检查 CANN 环境脚本、HF 权重、DCP 权重、SFT 数据、MindSpeed-MM 训练器、`npu-smi`，以及 `torch`、`torch_npu`、`transformers`、`mindspeed_mm` 是否可导入。

### `ascend/convert_qwen35_weight.sh`

调用附件 7 的 `GenericDCPConverter`，把 HuggingFace 格式的 Qwen3.5 权重转换为 MindSpeed-MM 训练所需的 DCP 格式。需要合法模型权重和完整 MindSpeed-MM 仓库。

### `ascend/prepare_ascend_run.py`

便携配置渲染器。接收服务器上的 HF 和 DCP 真实路径，为 `baseline`、`runtime-optimized`、`memory-optimized` 创建三个 YAML，并生成实验目录、profiling 目录和运行清单。

### `ascend/run_experiment_matrix.sh`

三组实验总调度脚本：

- `baseline`：关闭 task queue、memory reuse 和 CPU affinity。
- `runtime-optimized`：开启 task queue、memory reuse、CPU affinity 和可扩展内存段。
- `memory-optimized`：使用运行时优化参数，并由 YAML 开启重计算、profiling 和显存分析。

三组完成后调用 `compare_npu_experiments.py` 生成对比。

### `ascend/finetune_qwen35_kaoyan.sh`

单组 MindSpeed-MM 微调启动器。加载 CANN 环境，设置 NPU 优化变量和分布式参数，使用 `torchrun mindspeed_mm/fsdp/train/trainer.py` 启动训练，保存原始日志并自动解析指标。该文件在当前 ZIP 中存在一个缺失外层 `fi` 的 shell 语法问题，真实上机前必须修复并执行 `bash -n` 检查。

### `ascend/export_qwen35_weight.sh`

训练后权重导出工具。把 DCP 检查点转回 HuggingFace 格式，使 `transformers` 推理服务可以加载微调后的模型。

### `ascend/qwen35_ascend_server.py`

真正面向昇腾 NPU 的 Qwen3.5 推理服务骨架。使用 `torch_npu` 和 `transformers` 把模型加载到 `npu`，提供 `/health` 和 Qwen Chat的 `/api/qwen/generate`。当前实现串行保护模型生成并返回 token 数和总生成时延；必须在真实昇腾环境、真实权重和匹配版本依赖下验证。

## 九、`docs/` 技术与答辩文档，共 13 个

### `docs/ascend_server_runbook.md`

昇腾服务器逐步上机手册。从前置环境、构建数据、权重转换、配置渲染、三组训练、导出推理到连接 Skill 和回填报告，适合真正拿到 NPU 服务器时照着执行。

### `docs/ascend_technical_route.md`

昇腾赛道总体技术路线。说明作品为何不只是网页 RAG，而是“知识库 + Agent + Qwen3.5 + MindSpeed-MM + 昇腾优化”，并列出分阶段实现计划和答辩口径。

### `docs/attachment7_mindspeed_mm_analysis.md`

对附件 7 官方 MindSpeed-MM 仓的结构分析。解释 Qwen3.5 转换、训练配置、Qwen3VL/COCO 关系和官方日志可提取指标，是项目昇腾脚本设计依据。

### `docs/attachment_compliance_matrix.md`

附件 1 至 8 与项目文件的逐项对应表。用于证明项目没有遗漏创意书、运行样例、性能报告、数据集、功能精度流程、日志、样例仓和框架介绍等要求。

### `docs/competition_notes.md`

比赛要求阅读记录。保存公开信息、附件读取状态和这些要求对项目设计的影响，属于工作底稿。

### `docs/competition_rules_analysis.md`

对正式规程 PDF 的提炼。记录初赛、复赛、决赛截止时间与提交内容，说明创新、功能、性能和商业评分怎样映射到本项目。

### `docs/demo_script.md`

演示和答辩脚本。安排专业知识、真题、院校、时效风险和规划五个演示问题，并准备昇腾技术路线的讲法和常见追问。

### `docs/full_project_roadmap.md`

项目总路线图。把初赛、复赛和总决赛的交付物、时间点以及技术/汇报分工列出来。

### `docs/judge_qna.md`

评委问答口径。解释与通用大模型的区别、专业和学校选择、数据可靠性、年份控制、技术创新、昇腾流程、当前边界和扩展方向。

### `docs/next_steps_non_technical.md`

面向非技术成员的下一步任务说明。把资料链接收集、汇报准备与技术实现分开，帮助团队协作。

### `docs/skill_runtime_api.md`

Skill API 文档。说明 `/api/skill/invoke` 的请求和响应结构，以及通过环境变量连接模型服务的方法，供系统集成或评委查看。

### `docs/submission_draft.md`

早期初赛创意书草稿。记录项目背景、目标、功能、技术路线、创新点和风险；最终正式版本以 `submissions/initial_round/` 为准。

### `docs/yz_chsi_data_strategy.md`

研招网数据接入策略。说明哪些板块适合使用、如何登记来源、人工整理卡片、导入知识库、保留年份和采集日期，以及为何不能把研招网当作唯一答案来源。

## 十、`reports/` 测试与证据，共 12 个

### `reports/accuracy_log_template.md`

真实模型精度日志空白模板。设计事实一致性、引用命中、场景完整性、风险提示和表达可用性五个维度。当前表中是“待测”，需要真实 Qwen3.5 输出和人工评分后填写。

### `reports/benchmarks/local-rag-baseline.json`

本地性能基准的完整机器可读结果。包含 50 次调用的逐条耗时、提供方和汇总统计。所有调用均为 `local-template`，用于测 RAG/Agent 本地开销，不代表模型推理性能。

### `reports/benchmarks/local-rag-baseline.md`

上述 JSON 的人类可读摘要。记录平均 3.49 ms、P50/P95 和请求吞吐，并明确本地模板不能代替昇腾 NPU/Qwen3.5 实测。

### `reports/competition_submission_checklist.md`

比赛阶段检查表。分别列出初赛已完成项、复赛待完成项，以及不能提前声称的 NPU、模型、COCO 和数据库能力。

### `reports/functional_test_log.md`

四类本地功能测试结果。当前为 4/4 通过，证明四种 Agent 路由、引用和关键结构可工作，不证明模型泛化能力。

### `reports/initial_submission_validation.md`

初赛自动自检结果。记录创意书 1038 字、PDF 5 页、ZIP 无嵌套归档并通过结构检查，同时提醒团队信息、签名和最终文件名仍需人工处理。

### `reports/npu_evidence_checklist.md`

复赛 NPU 证据归档清单。列出环境版本、转换日志、三组训练日志、profiling、显存、推理健康检查、模型基准和 50 题精度日志应该放在哪里。当前均待上机。

### `reports/official_sample_evidence/qwen35_0.8B_20260608_110844.metrics.json`

从附件 7 官方 Qwen3.5 样例日志解析出的完整指标和每步数据。用途是验证日志解析器、理解官方指标格式；它不是本项目训练结果。

### `reports/official_sample_evidence/qwen35_0.8B_20260608_110844.metrics.md`

官方样例指标摘要，包含 step time、samples/s、loss 和显存。答辩时只能称为“附件 7 官方样例参考”，不能称为“我们实测”。

### `reports/performance_report_template.md`

复赛性能报告模板。预留测试环境、训练性能、推理性能、优化记录和结论，列明 baseline、runtime-optimized、memory-optimized 的比较口径。所有“待测”必须由真实 NPU 日志回填。

### `reports/rule_regression_log_local.md`

50 题本地规则回归的完整明细和汇总。它检查固定关键词、预期引用、Agent 路由、风险提示和回答长度。即使显示 100%，也不能称为真实 Qwen3.5 精度。

### `reports/sample_skill_response.json`

一次院校咨询 Skill 返回示例，用于展示 JSON 结构和引用。该静态样例仍标记 Skill `0.2.0`，而当前服务器为 `0.3.0`，因此只能作结构参考，正式材料应重新生成。

## 十一、`submissions/initial_round/` 初赛材料，共 5 个

### `submissions/initial_round/project_creative_book_1000.md`

正式创意书正文源文件，包含创意描述、需求与市场价值、技术方案、功能进展和排期。正文约 1038 个非空白字符，是 DOCX/PDF 生成脚本的内容来源。

### `submissions/initial_round/01-作品说明文档-待填写队伍名称.docx`

可编辑的附件 1 正式 Word 文档。包含封面、团队信息、原创声明、创意书和 Demo 附录。学校、队名、成员、导师、联系方式和签名仍是占位内容，不能原样上传。

### `submissions/initial_round/01-作品说明文档-待填写队伍名称.pdf`

当前 5 页正式 PDF 版式文件。它是最终上传格式的基础，但同样包含报名与签名占位符，文件名也尚未替换为真实队伍名称。

### `submissions/initial_round/README_submit.md`

初赛提交操作说明。列出建议上传内容、启动方式、Skill 调用、已验证规模、真实性边界和提交前自检命令。

### `submissions/initial_round/source_package_manifest.md`

源码包清单和打包说明。列出压缩包包含与排除的内容，强调不包含 Qwen3.5 权重、COCO 大数据集、缓存、嵌套压缩包和虚构 NPU 日志。

## 十二、哪些文件可以改，哪些应由脚本生成

建议人工维护：

- `data/knowledge_base.json`
- `data/knowledge_expansion.json`
- `data/source_cards_sample.json`
- `data/source_registry.json`
- `data/project_scope.json`
- `data/eval_questions*.json`
- `submissions/initial_round/project_creative_book_1000.md`
- `docs/` 中的说明文档

建议通过脚本重新生成，不要只手改结果：

- `ascend/annotations_slim.json`
- `ascend/dataset_manifest.json`
- `reports/functional_test_log.md`
- `reports/rule_regression_log_local.md`
- `reports/benchmarks/*`
- `reports/npu_raw/*` 和 NPU 对比报告
- 正式 DOCX/PDF
- 最终 ZIP

推荐的数据更新顺序：

```text
修改知识和来源
  -> build_mindspeed_sft_dataset.py
  -> functional_test.py
  -> run_eval.py
  -> benchmark_skill.py
  -> 生成正式文档
  -> validate_initial_submission.py
  -> package_initial_submission.py
  -> 再次自检
```

## 十三、当前源码包必须知道的边界

1. 当前本地回答默认来自 `local-template`，不是 Qwen3.5。
2. `ascend/` 是可执行工程骨架，但压缩包中没有模型权重、CANN、MindSpeed-MM 完整仓和真实 NPU。
3. `finetune_qwen35_kaoyan.sh` 当前存在缺失 `fi` 的语法问题，复赛上机前必须修复。
4. `preflight_check.sh` 同时检查 DCP 权重，而 README 的顺序把预检放在转换前；首次上机时应拆成转换前/转换后检查或调整顺序。
5. `official_sample_evidence/` 是附件 7 官方样例，不是我们的成绩。
6. 50 题日志是规则回归，不是大模型精度。
7. 正式 DOCX/PDF 仍有团队信息与签名占位符。
8. 当前 ZIP 未包含后来新增的用户需求与市场调研文档，若决定加入，需要重新执行打包和完整验证。

## 十四、你最需要记住的六个文件

如果暂时记不住 71 个文件，先记住下面六个：

| 文件 | 一句话记忆 |
| --- | --- |
| `run.ps1` | Windows 启动按钮 |
| `src/server.py` | 对外提供网页和 API |
| `src/rag_engine.py` | 检索与四类 Agent 的核心大脑 |
| `src/model_gateway.py` | 连接真实 Qwen3.5 的桥梁 |
| `data/knowledge_base.json` | 首批知识内容 |
| `ascend/README.md` | 复赛上昇腾服务器的入口说明 |

一句话概括整个源码包：它已经是一套可独立运行的考研 RAG Agent 初赛原型，并准备了通向 MindSpeed-MM/Qwen3.5 昇腾训练与推理的工程链，但真实 NPU 训练、模型精度和性能成绩尚未产生。
