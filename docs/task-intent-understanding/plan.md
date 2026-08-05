# 任务意图理解与纠正 Plan

## 架构概览

新增独立意图模块，提供确定性提取器、模型提取器、补丁清洗和深度合并。聊天流程
保留同步入口供测试及降级使用，新增异步入口调用模型。Gateway 和 WebChat 使用异步
入口；任务服务仍是唯一持久化边界。

## 核心数据结构

### `TaskIntentResult`

- `intent`：create、update、confirm、cancel、list、none。
- `patch`：只允许任务白名单字段。
- `confidence`：0 到 1。
- `clarification`：当前能力无法安全表达时的追问。

### `TaskIntentExtractor`

异步 `extract(text, current_draft)`，返回 `TaskIntentResult` 或空值。

## 模块设计

### 确定性意图层

解析创建命令、中文/数字时间间隔、通知渠道、否定纠正和简洁目标；作为同步默认和
模型失败回退。

### 模型意图层

调用现有 provider，要求仅返回 JSON。解析后经过字段白名单、类型和范围清洗；不
暴露数据库与工具能力。

### 草稿合并与校验层

把补丁合并到当前结构化草稿，调用现有 normalize 和 TaskService 边界校验。完整目标
更新时同步生成来源关键词。已有暂停任务通过版本更新复用同一 task_id。

### Gateway 接入层

飞书和 WebChat await 异步任务入口；无模型 provider 时自然降级。

## 文件组织

```text
backend/src/watchlight/scheduler/intent.py       — 意图、提取、清洗与合并
backend/src/watchlight/scheduler/normalize.py    — 使用结构化确定性提取
backend/src/watchlight/scheduler/nl.py           — 草稿状态与异步模型入口
backend/src/watchlight/gateway/boot_watchshed.py — 注入模型提取器
backend/src/watchlight/gateway/boot.py            — await 异步入口
backend/src/watchlight/gateway/methods/sessions.py — WebChat 异步入口
tests/watchlight/test_task_intent.py              — 理解、纠正与模型降级测试
```

## 技术决策

| 决策点 | 选择 | 理由 |
|---|---|---|
| 模型职责 | 只提取 JSON 补丁 | 防止模型直接执行业务动作 |
| 数据模型 | 保留 frequency_seconds | 控制本次改动范围并兼容数据库 |
| 同步兼容 | 保留 handle，新增 handle_async | 避免破坏现有服务与测试调用方 |
| 降级 | 增强确定性解析 | 模型/API 故障时核心功能仍可用 |
| 修正持久化 | 更新原暂停任务版本 | 避免重复孤儿任务 |
