# 关注任务查询一致性修复 Plan

## 架构概览

修复采用两条互补但共享同一数据访问层的查询路径：

1. **确定性任务对话路径**：现有自然语言任务流程在处理创建/确认之前先识别常见的任务列表意图，直接通过任务服务读取数据库并生成用户可读回复。这条路径覆盖高频问法，不调用模型。
2. **大模型只读工具路径**：为没有命中确定性规则的语义变体提供 `watch_tasks_list` 工具。工具没有 `user_id` 输入参数，只能读取网关在身份解析后放入执行上下文的规范用户身份。

两条路径复用同一个任务视图与格式化模块，避免状态、频率和通知渠道展示不一致。飞书和 Web 中被确定性流程提前响应的问答通过网关统一的会话记录接口写入 transcript。

```text
飞书/Web 入站
    → IdentityRegistry.resolve_or_register
    → canonical user_id
    → NaturalLanguageTaskFlow.handle
        ├─ 命中列表意图 → TaskService.list → TaskView → 直接回复
        ├─ 命中创建/确认 → TaskService.create/confirm → 直接回复
        └─ 未命中 → AgentRunRequest(metadata.userId)
                         → watch_tasks_list(ToolContext.user_id)
                         → TaskService.list → 结构化工具结果 → 模型回复

所有“直接回复” → GatewayRuntime.record_session_exchange → transcript
```

## 核心数据结构与接口

### TaskView

供确定性回复和模型工具共同使用的稳定只读视图：

```python
class TaskView(TypedDict):
    task_id: str
    target: str
    status: str
    status_label: str
    frequency_seconds: int
    frequency_label: str
    notification_channels: list[str]
    notification_channel_labels: list[str]
```

视图不暴露原始 JSON 列、其他用户标识或内部版本记录。

### TaskService.list

```python
def list(self, user_id: str) -> list[dict[str, Any]]
```

通过 `TasksRepo.for_user(...).list()` 返回当前用户未删除任务。它是确定性查询与只读工具的统一业务入口。

### 任务列表意图与格式化

```python
def is_task_list_intent(text: str) -> bool
def task_to_view(task: Mapping[str, Any]) -> TaskView
def format_task_list(tasks: Sequence[Mapping[str, Any]]) -> str
```

- 意图识别同时要求出现任务语义和查询/回顾语义，避免把“创建关注任务”误识别成查询。
- `format_task_list` 对空列表输出明确空状态；对多个任务逐条展示目标、状态、频率和通知渠道。
- 数据库访问异常由任务对话流程捕获并返回“暂时无法查询”，不伪装成空列表。

### watch_tasks_list 工具

```python
def create_watch_tasks_list_tool(store: Store) -> ToolDefinition
```

- 输入 schema 为空，不允许模型传入用户 ID。
- handler 从 `ToolContext.user_id` 取得规范身份；缺失时抛出明确错误。
- 输出 `{count: int, tasks: list[TaskView]}`。
- 只在 Watchlight 业务服务装配成功后注册到共享工具注册表。

### ToolContext 身份扩展

```python
@dataclass
class ToolContext:
    ...
    user_id: str | None = None
```

`GatewayRuntime.run_agent_for_session` 接收内部参数 `user_id`，放入 `AgentRunRequest.metadata["userId"]`；`EmbeddedRuntime` 再将其复制到 `ToolContext.user_id`。外部模型只能看到工具的空参数 schema，不能覆盖该值。

### GatewayRuntime.record_session_exchange

```python
def record_session_exchange(
    self,
    session_key: str,
    user_message: str,
    assistant_message: str,
    *,
    channel: str | None = None,
    route_patch: dict[str, Any] | None = None,
) -> None
```

确保 session 存在，按顺序追加 user/assistant 两条 transcript，更新渠道和最近路由并保存 session 索引。仅用于没有进入 `run_agent_for_session` 的确定性回复，避免重复记录普通模型轮次。

## 模块设计

### 自然语言任务流程

**职责：** 识别任务列表意图；协调创建、确认与列表查询；生成确定性回复。

**对外接口：** 保持现有 `handle(user_id, channel, text) -> str | None`，避免改变渠道调用约定。

**依赖：** `TaskService`、任务展示模块。

### 任务展示模块

**职责：** 将存储行转换为安全、稳定的任务视图，并生成人类可读列表。

**对外接口：** `task_to_view`、`format_task_list`、现有频率/渠道名称格式化能力。

**依赖：** 仅标准库；不访问数据库。

### 关注任务只读工具

**职责：** 让模型在受控上下文中查询当前用户任务。

**对外接口：** 工具定义工厂。

**依赖：** `TaskService` 或 `TasksRepo`、任务展示模块、`ToolContext`。

### 网关与嵌入式运行时

**职责：** 在身份解析后传播规范用户身份；为确定性回复维护会话历史。

**对外接口：** 扩展 `run_agent_for_session` 内部参数；新增 `record_session_exchange`。

**依赖：** `IdentityRegistry`、`SessionStore`、`TranscriptManager`。

### 系统提示与工具策略

**职责：** 允许远程消息入口使用 `watch_tasks_list`，并明确任务存在性只能以该工具或确定性业务查询为依据。

**依赖：** 现有工具策略与 System Prompt 构建器。

## 模块交互

### 确定性列表查询

1. 网关解析飞书或 Web 渠道身份为规范 `user_id`。
2. `NaturalLanguageTaskFlow` 判断消息是否为任务列表意图。
3. 命中后调用 `TaskService.list(user_id)`。
4. 任务展示模块将结果格式化为用户可读文本。
5. 网关将输入和回复写入对应 session transcript，再向渠道发送回复。

### 模型工具查询

1. 未命中确定性流程的消息进入 `run_agent_for_session(user_id=...)`。
2. 网关把 `userId` 写入内部 metadata。
3. Embedded Runtime 构造带 `user_id` 的 `ToolContext`。
4. 模型调用无参数的 `watch_tasks_list`。
5. 工具按上下文身份读取任务，并返回 `TaskView` 列表。
6. 模型依据工具结果回答；系统提示禁止以会话/记忆结果代替任务结果。

### 确定性回复会话落盘

1. 飞书使用 `resolve_session_key(message)`；Web 使用请求已有的 `sessionKey`。
2. 网关调用 `record_session_exchange`。
3. 接口创建或复用 session，顺序追加 user/assistant 消息并保存路由元数据。
4. 后续模型轮次读取到完整历史，但不会重复写入本轮确定性回复。

## 文件组织

```text
backend/src/watchlight/
├── scheduler/
│   ├── service.py                  — 增加按用户列出任务的业务入口
│   ├── nl.py                       — 增加列表意图和确定性查询分支
│   └── presentation.py             — 新建任务视图与列表格式化
├── tools/
│   ├── builtin/watch_tasks.py      — 新建只读任务列表工具
│   ├── types.py                    — ToolContext 增加规范 user_id
│   └── policy.py                   — messaging 允许只读任务工具
├── agents/
│   ├── runtime/embedded/runner.py  — 从 metadata 注入 ToolContext.user_id
│   └── system_prompt/builder.py    — 强化任务查询真实性约束
└── gateway/
    ├── boot.py                     — 传播身份并记录确定性问答
    ├── boot_watchshed.py           — 业务服务启动后注册任务工具
    └── methods/sessions.py         — Web 路径传播身份并记录确定性问答

tests/watchlight/
├── test_channels_nl_create.py      — 列表意图、格式与异常行为
├── test_channels_identity.py       — 飞书身份传播和 transcript 集成
├── test_gateway_methods.py         — Web 确定性回复落盘
├── test_watch_tasks_tool.py        — 新建工具身份隔离与结构化输出测试
├── test_system_prompt.py           — 查询真实性提示约束
└── test_boot.py                    — 工具装配与 messaging 权限
```

## 技术决策

| 决策点 | 选择 | 理由 |
|---|---|---|
| 高频列表查询 | 确定性意图直接查询 | 不依赖模型是否正确选工具，稳定复现用户预期 |
| 长尾自然语言 | 同时提供只读模型工具 | 覆盖固定关键词规则无法穷举的表达 |
| 用户身份来源 | 仅使用网关解析后的 ToolContext | 防止模型参数造成越权或跨用户读取 |
| 工具注册时机 | 业务 Store 初始化后注入共享 Registry | 默认工具工厂创建时数据库尚未装配；共享 Registry 可被已创建 Runtime 动态读取 |
| 展示逻辑 | 确定性回复与工具共享 TaskView | 避免两个查询路径字段和名称漂移 |
| 会话一致性 | 网关统一记录提前返回的问答 | transcript 属于网关基础设施，业务流程不直接依赖文件会话实现 |
| 查询异常 | 显式失败，禁止降级为空 | 空列表是业务事实，异常是系统状态，两者必须可区分 |
| 修改范围 | 仅列表只读能力 | 满足本次问题，避免扩大到高风险任务写操作 |

## Spec 覆盖

| Spec | 设计归属 |
|---|---|
| F1–F3 | 自然语言任务流程、TaskService.list、任务展示模块 |
| F4 | watch_tasks_list、ToolContext 身份传播、工具策略 |
| F5 | GatewayRuntime.record_session_exchange、飞书/Web 接入 |
| F6 | 系统提示与工具结果约束 |

所有功能需求均有对应模块和调用链；模块依赖由网关/装配层指向业务层，不引入业务层对网关或 session 文件实现的反向依赖。
