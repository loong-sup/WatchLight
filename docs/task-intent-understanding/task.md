# 任务意图理解与纠正 Tasks

## 文件清单

| 操作 | 文件 | 职责 |
|---|---|---|
| 新建 | `backend/src/watchlight/scheduler/intent.py` | 结构化意图与提取器 |
| 修改 | `backend/src/watchlight/scheduler/normalize.py` | 使用确定性补丁 |
| 修改 | `backend/src/watchlight/scheduler/nl.py` | 增量合并和异步入口 |
| 修改 | `backend/src/watchlight/gateway/boot_watchshed.py` | 模型提取器装配 |
| 修改 | `backend/src/watchlight/gateway/boot.py` | 飞书异步调用 |
| 修改 | `backend/src/watchlight/gateway/methods/sessions.py` | WebChat 异步调用 |
| 新建 | `tests/watchlight/test_task_intent.py` | 新能力回归测试 |

## T1：结构化意图与确定性提取

实现数据结构、数字时间解析、目标清理、补丁白名单、合并和固定时间澄清。

**验证：** 意图单元测试覆盖 5 小时、每天、否定纠正和非法补丁。

## T2：模型 JSON 提取器

实现受限提示词、流式文本收集、JSON 提取、清洗及异常回退。

**验证：** 模拟 provider 的合法、非法输出测试通过。

## T3：聊天草稿增量合并

重构创建流程使用 TaskIntentResult；完整重述和纠正更新同一暂停任务。

**验证：** 截图对应端到端对话测试通过且数据库只有一条暂停任务。

## T4：Gateway 异步接入

装配当前默认 provider，并让飞书/WebChat 调用 handle_async。

**验证：** Gateway 身份与任务集成测试通过。

## T5：全量验收

运行 Ruff、新增测试和完整 pytest。

**验证：** 所有检查通过。

## 执行顺序

```text
T1 → T2 → T3 → T4 → T5
```
