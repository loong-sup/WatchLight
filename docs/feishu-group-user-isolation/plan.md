# 飞书群聊多用户会话隔离 Plan

## 架构概览

入站飞书事件先规范化消息正文和发送者身份；统一路由随后用群 ID 与发送者 ID
生成用户级群聊会话键；Gateway 继续使用原群 ID 作为回复目标，并在 transcript 的
用户消息记录中写入发送者元数据。旧群级会话不做迁移。

## 核心接口

### `parse_inbound(event_data, bot_open_id=None)`

解析飞书事件。根据 `mentions` 中的 key、用户 ID 和名称清除机器人占位符，并将
其他真人提及转换为可读名称。

### `resolve_session_key(message)`

私聊返回原有用户级键；群聊返回包含群 ID 和发送者 ID 的稳定键。

### `run_agent_for_session(..., sender_id=None, user_id=None)`

写入用户 transcript 时附加可选的 `senderId` 和 `userId`。

### `record_session_exchange(..., sender_id=None, user_id=None)`

确定性任务回复路径同样保存发送者元数据。

## 模块设计

### 飞书消息解析

**职责：** 解析 mentions、判断机器人是否被提及、规范化正文。
**依赖：** 飞书事件 payload 和可选的机器人 open_id 配置。

### 会话路由

**职责：** 将群聊默认路由切换为 per-sender，保持私聊和显式绑定规则不变。
**依赖：** 标准化消息中的 channel、conversationId、senderId 和 chatType。

### Gateway transcript

**职责：** 模型路径与确定性任务路径都保存发送者标识，同时仍向原会话发送回复。
**依赖：** 身份注册结果和现有 TranscriptManager。

## 模块交互

```text
飞书事件
  → 提及规范化与发送者解析
  → 群 ID + 发送者 ID 路由
  → 身份解析
  → 独立 transcript / 模型上下文
  → 回复原群 ID
```

## 文件组织

```text
backend/src/watchlight/channels/feishu/message.py  — 提及规范化
backend/src/watchlight/channels/feishu/plugin.py   — 传入机器人身份
backend/src/watchlight/channels/routing.py         — per-sender 群路由
backend/src/watchlight/gateway/boot.py              — transcript 发送者元数据
tests/watchlight/test_feishu_group_isolation.py     — 路由、解析、集成回归
```

## 技术决策

| 决策点 | 选择 | 理由 |
|---|---|---|
| 群上下文 | 默认按发送者隔离 | 满足隐私和上下文不串线目标 |
| 旧会话 | 保留但停止续写 | 旧数据没有可靠发送者信息，不能安全拆分 |
| 回复目标 | 继续使用原群 ID | 会话存储隔离不应改变用户可见回复位置 |
| 提及回退 | 无 botOpenId 时使用首个提及作为机器人 | 兼容当前配置和 group-at-message 事件 |
| transcript | 增加可选元数据字段 | 保持旧 JSONL 可读且便于诊断 |
