# Skill Runtime API

## HTTP 接口

- `GET /api/health`：服务和模型网关状态。
- `GET /api/status`：Skill 版本、知识条目数、专业和模型连接状态。
- `POST /api/ask`：网页应用调用。
- `POST /api/skill/invoke`：正式 Skill 调用。

请求示例：

```json
{
  "question": "真题解析：为什么 TCP 建立连接需要三次握手？",
  "mode": "exam",
  "specialty": "计算机",
  "profile": {"target": "清华大学", "days": "120", "level": "基础一般"}
}
```

响应 `output` 包含：Agent 路由、回答、置信度、引用元信息、风险提示、模型提供方、模型错误、usage、检索/生成/总耗时和证据统计。当前 Skill 版本为 `0.3.0`。

## 模型网关

Qwen Chat服务：

```text
KAOYAN_MODEL_ENDPOINT=http://127.0.0.1:8000/api/qwen/generate
KAOYAN_MODEL_PROTOCOL=qwen
KAOYAN_MODEL_NAME=Qwen3.5-0.8B-Kaoyan
KAOYAN_MODEL_API_KEY=可选
```

原生服务也可使用 `KAOYAN_MODEL_PROTOCOL=native`，接收 `prompt`、`mode`、`context` 并返回 `answer`、`text` 或 `response`。

模型不可用时 demo 会回退到本地模板并在 `model_error` 中保留原因。正式性能和精度测试必须使用：

```bash
python scripts/benchmark_skill.py --limit 50 --label ascend-qwen35 --require-external-model
```

这样只要发生一次回退，测试就会失败，避免误报。
