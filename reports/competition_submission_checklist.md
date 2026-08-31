# 比赛提交检查表

更新时间：2026-07-21

## 初赛，截止 2026-07-26 24:00

| 项目 | 状态 | 文件 |
| --- | --- | --- |
| 约 1000 字项目创意书 | 正文已完成，报名字段待填 | `submissions/initial_round/01-作品说明文档-待填写队伍名称.docx`、`.pdf` |
| 最小可运行 demo | 已完成 | `run.ps1`、`static/`、`src/server.py` |
| Skill Runtime | 已完成 | `POST /api/skill/invoke`、`scripts/skill_cli.py` |
| 源码压缩包 | 已生成并自检 | 无嵌套ZIP/RAR/7z，见 `reports/initial_submission_validation.md` |
| 本地规则回归日志 | 已完成 | `reports/rule_regression_log_local.md`，不等价于模型精度 |
| 功能验证日志 | 已完成 | `reports/functional_test_log.md` |
| 数据与评测规模 | 已完成 | 64 条知识、192 条 SFT、50 条评测 |
| 昇腾技术路线 | 已完成可执行链 | `ascend/`、`docs/ascend_server_runbook.md` |
| 附件合规说明 | 已完成 | `docs/attachment_compliance_matrix.md`、`docs/competition_rules_analysis.md` |

## 复赛，截止 2026-09-30 24:00

| 项目 | 状态 | 说明 |
| --- | --- | --- |
| 约 2000 字完整创意书 | 待扩展 | 基于初赛创意书扩写 |
| 可运行完整 Skill | 接口与网关已完成 | Qwen Chat网关已验证，真实 Qwen3.5 推理待 NPU 上机 |
| Qwen3.5 权重转换 | 转换/导出脚本已准备 | 需昇腾环境和合法权重 |
| MindSpeed-MM 微调 | 三组实验链已准备 | 需昇腾 NPU 实跑并归档原始日志 |
| 精度测试日志 | 本地预演完成 | 正式日志需 NPU/Qwen3.5 版本 |
| 性能分析报告 | 模板和自动解析已准备 | 需回填吞吐、时延、显存、loss |
| COCO/官方样例数据要求 | 待确认实跑 | 附件 4 数据较大，复赛按赛题说明处理 |

## 不能提前声称的内容

- 不能声称已完成真实昇腾 NPU 性能优化。
- 不能声称已使用完整 Qwen3.5 权重实测。
- 不能声称已下载并跑通 COCO 数据集。
- 不能把样例知识库说成完整研招网数据库。
