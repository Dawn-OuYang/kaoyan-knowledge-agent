# 附件 1-8 合规矩阵

更新时间：2026-07-21

## 读取状态说明

用户已提供附件 1-8 的明确链接和用途说明，并额外提供附件 7 压缩包副本。当前环境可访问部分页面和直链文件元信息，但 Chaspark 动态详情、昇腾论坛帖子正文仍可能需要浏览器登录或页面权限。技术路线已按用户提供的附件名称、链接、附件 7 官方样例代码和可访问信息完成重构。

## 附件清单与项目应对

| 附件 | 名称/用途 | 链接或来源 | 对项目的硬性影响 | 当前应对 |
| --- | --- | --- | --- | --- |
| 附件 1 | 初赛（昇腾赛道）项目创意书模板 | Chaspark 热点 `1281051832178561024` | 封面、团队信息、原创声明、约1000字正文、选交demo；最终PDF提交 | 已生成正式DOCX/PDF，正文约1000字；报名信息与签名待队伍补齐 |
| 附件 2 | 运行样例和赛题说明 | HiAscend 帖子 `02189216381620121009` | 技术路线必须对齐官方运行样例，不只是普通 Web Demo | 项目技术线升级为“应用 Agent + 昇腾赛题样例适配” |
| 附件 3 | 性能分析报告模板 | Chaspark 热点 `1283237378107756544` | 需要输出性能分析报告，包括环境、指标、瓶颈、优化 | 已新增 `reports/performance_report_template.md`，后续补真实 NPU 数据 |
| 附件 4 | COCO 数据集 | `dataset.rar` | 赛题验证可能要求使用 COCO 数据集或样例数据 | 保留 COCO 数据处理与验证接口，暂不下载大文件 |
| 附件 5 | 功能、精度验证和性能说明 | HiAscend 帖子 `02178217915304837030` | 必须说明功能验证、精度验证、性能验证方法 | 新增三类验证方案：功能用例、精度日志、吞吐/时延 |
| 附件 6 | 精度测试日志 | HiAscend 帖子 `02194217916581366040` | 需要保存/提交精度测试日志 | 已新增 `reports/accuracy_log_template.md` 和测试样例字段 |
| 附件 7 | 代码样例 | 昇腾赛道官方 QQ 群 1103080324，文件名：`赛题参考样例-MindSpeed-MM仓的代码.rar` | 需要参考 MindSpeed-MM 官方样例结构 | 用户已提供压缩包；已解压副本并分析 `examples/qwen3_5`、`examples/qwen3vl`、Qwen3.5 配置、转换脚本、微调脚本和官方日志 |
| 附件 8 | MindSpeed MM 框架与 Qwen3.5 模型结构介绍 | OBS MP4 直链 | 技术说明必须体现 MindSpeed-MM 与 Qwen3.5 模型结构 | 技术路线已加入 MindSpeed-MM/Qwen3.5 适配层 |

## 结论

项目不能只做“考研知识库问答网页”。正式参赛技术路线应为：

```text
考研知识库问答场景
  + RAG/Agent 应用层
  + MindSpeed-MM / Qwen3.5 模型适配层
  + 昇腾 NPU 运行与性能分析
  + 功能、精度、性能三类验证材料
```

之前的本地 MVP 保留为应用演示壳；后续开发重点转向昇腾赛题合规、模型运行样例、精度日志和性能报告。

## 附件 7 已落实的工程文件

```text
ascend/README.md
ascend/convert_qwen35_weight.sh
ascend/finetune_qwen35_kaoyan.sh
ascend/qwen3_5_kaoyan_config.yaml
ascend/annotations_slim.json
docs/attachment7_mindspeed_mm_analysis.md
reports/performance_report_template.md
reports/accuracy_log_template.md
```

当前已补齐预检、便携配置渲染、HF/DCP 双向转换、三组性能实验、日志自动解析、NPU 推理服务和强制禁止回退的模型基准。尚未产生本项目昇腾 NPU 实测数据；正式材料中的性能和模型精度数值必须在昇腾环境复跑后回填。

## 规程 PDF 补充要求

用户补充比赛规程 PDF 后，已确认昇腾赛道阶段性交付要求如下：

| 阶段 | 规程要求 | 当前项目文件 |
| --- | --- | --- |
| 初赛 | 约 1000 字项目创意书；最小可运行 demo 可选 | 正式DOCX/PDF、无嵌套归档源码包、`run.ps1`、`src/`、`static/` |
| 复赛 | 约 2000 字完整创意书；可运行完整 Skill；性能分析测试报告 | `docs/full_project_roadmap.md`、`/api/skill/invoke`、`ascend/`、`reports/performance_report_template.md` |
| 总决赛 | 不超过 5 分钟 demo 视频；demo PPT | `docs/demo_script.md` 已有基础稿，PPT 待后续生成 |

评分项对齐：

| 评分项 | 分值 | 项目对应 |
| --- | --- | --- |
| 创新性 | 30 | 考研专业课、院校核验、复习规划一体化 Agent Skill |
| 功能性 | 20 | 网页、HTTP Skill API、命令行、评测脚本 |
| 性能优化 | 40 | MindSpeed-MM/Qwen3.5 昇腾适配脚本和性能报告模板，真实数据待昇腾环境回填 |
| 商业性 | 10 | 面向考研辅导、个人备考和院校信息服务 |
| 附加分 | 10 | 后续整理开源仓并尝试 PR 合入 |
