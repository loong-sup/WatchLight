# 飞书群聊多用户会话隔离 Tasks

## 文件清单

| 操作 | 文件 | 职责 |
|---|---|---|
| 修改 | `backend/src/watchlight/channels/feishu/message.py` | 解析并清理飞书提及 |
| 修改 | `backend/src/watchlight/channels/feishu/plugin.py` | 向解析器提供机器人 open_id |
| 修改 | `backend/src/watchlight/channels/routing.py` | 群聊按发送者生成会话键 |
| 修改 | `backend/src/watchlight/gateway/boot.py` | 保存 transcript 发送者元数据 |
| 新建 | `tests/watchlight/test_feishu_group_isolation.py` | 单元与集成回归测试 |

## T1：实现飞书提及规范化

**依赖：** 无

1. 从 mentions 中读取 key、open_id 和 name。
2. 精确清除机器人 key；将其他用户 key 转换为可读提及。
3. 支持没有 botOpenId 和没有 mentions 的兼容路径。

**验证：** 解析群消息后正文不含机器人 `@_user_N`，真人提及仍可读。

## T2：实现群聊 per-sender 路由

**依赖：** 无

1. 修改默认群聊会话键，加入 senderId。
2. 保持私聊及显式绑定规则行为不变。

**验证：** 同群不同用户的键不同，同用户同群的键稳定。

## T3：保存 transcript 发送者元数据

**依赖：** T2

1. 模型执行路径写入 senderId 和 userId。
2. 确定性任务回复路径写入相同元数据。
3. 在入站处理处传递已解析身份。

**验证：** JSONL 用户记录可观察到对应发送者标识。

## T4：新增群聊多用户集成测试

**依赖：** T1、T2、T3

1. 覆盖 mention 清理和真人提及保留。
2. 覆盖同群双用户隔离、同用户延续、跨群隔离。
3. 覆盖任务路径 transcript 和原群回复目标。

**验证：** 新增测试文件全部通过。

## T5：完整回归

**依赖：** T4

1. 运行代码规范检查。
2. 运行完整测试套件。

**验证：** lint 与全部测试通过。

## 执行顺序

```text
T1 ─┐
    ├→ T4 → T5
T2 → T3 ┘
```
