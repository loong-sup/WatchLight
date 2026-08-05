# 飞书自然语言删除关注任务 Plan

## 架构概览

删除能力作为独立的确定性对话状态机接入现有 `NaturalLanguageTaskFlow`，不交给大模型决定，也不新增远程写工具。现有任务对话入口先把消息交给删除状态机；删除状态机未处理时，再继续现有列表查询和创建流程。

```text
飞书/Web 入站
  → 解析 canonical user_id + session_key
  → NaturalLanguageTaskFlow.handle(..., conversation_id=session_key)
      → NaturalLanguageDeleteFlow
          ├─ 发起删除 → 查询 active/paused 任务 → 展示名称/状态/完整 ID
          ├─ 输入关键词/ID → 在当前候选集合中匹配
          │    ├─ 0 个 → 保留候选，提示重试
          │    ├─ 多个 → 收窄候选，继续消歧
          │    └─ 1 个 → 保存唯一 task_id，展示删除确认摘要
          ├─ 取消 → 清除短期状态
          └─ 确认删除 → 原子 active|paused → draining
  → Gateway 复用 record_session_exchange 写入 transcript
  → SchedulerLoop 沿用 draining → deleted 收敛
```

## 核心数据结构与接口

### DeleteConversation

```python
@dataclass(slots=True)
class DeleteConversation:
    candidate_ids: tuple[str, ...]
    selected_task_id: str | None
    expires_at: float
```

- `candidate_ids` 是当前消歧范围；首次发起时包含所有可删除任务，每次多候选匹配后收窄。
- `selected_task_id` 非空表示进入待确认阶段。
- `expires_at` 使用进程内单调时钟，任一有效选择交互后刷新为 10 分钟。

状态字典的键为：

```python
DeleteScope = tuple[str, str, str]  # canonical user_id, channel, conversation_id
```

没有传入 `conversation_id` 的旧调用使用稳定空串作为兼容作用域；飞书和 Web 生产入口必须传入 `session_key`。

### NaturalLanguageDeleteFlow

```python
class NaturalLanguageDeleteFlow:
    def __init__(self, tasks: TaskService, ttl_seconds: int = 600) -> None: ...

    def handle(
        self,
        user_id: str,
        channel: str,
        conversation_id: str,
        text: str,
        *,
        now: float | None = None,
    ) -> str | None: ...
```

行为顺序：识别重新发起、检查已有状态及过期、处理取消、处理确认、处理关键词/ID选择。没有删除意图且没有本会话删除状态时返回 `None`。

### NaturalLanguageTaskFlow 扩展

```python
def handle(
    self,
    user_id: str,
    channel: str,
    text: str,
    conversation_id: str | None = None,
    *,
    now: float | None = None,
) -> str | None: ...
```

先委托删除流程。现有创建 pending key 同步扩展为 `(user_id, channel, conversation_id)`，避免不同飞书会话共享确认状态；不传 conversation ID 的现有测试和调用保持原行为。

### TaskService 删除接口

```python
def list_deletable(self, user_id: str) -> list[dict[str, Any]]: ...

def confirm_delete(self, user_id: str, task_id: str) -> dict[str, Any] | None: ...
```

- `list_deletable` 只返回 `active`、`paused`。
- `confirm_delete` 调用 repository 原子条件更新；目标不存在、不属于用户或状态已变化时返回 `None`。
- 现有 REST 使用的 `delete` 接口保持不变，避免改变当前 API 兼容行为。

### TasksRepo 原子状态转换

```python
def begin_draining(self, task_id: str) -> dict[str, Any] | None: ...
```

单条条件更新：仅当 `task_id`、repo 自带的 `user_id` 命中且状态属于 `active|paused` 时更新为 `draining`。通过受影响行数判断成功，避免“确认前复核”和“实际更新”之间的竞态。

### 删除展示函数

```python
def format_delete_candidates(tasks: Sequence[Mapping[str, Any]], *, narrowed: bool) -> str: ...
def format_delete_confirmation(task: Mapping[str, Any]) -> str: ...
```

候选展示使用现有 `TaskView` 状态标签并显示完整任务 ID；确认摘要明确停止后续执行和通知，并只提示“确认删除”或“取消”。

## 匹配与状态规则

### 发起意图

确定性识别明确命令：`删除任务`、`删除关注任务`、`我要删除任务`、`我要删除关注任务`、`帮我删除任务`、`帮我删除关注任务`。不把“如何删除任务”自动当作写操作。

### 名称关键词匹配

1. 对输入和任务名称执行 Unicode `casefold` 后做包含匹配。
2. 完整任务 ID优先做区分大小写的精确匹配。
3. 匹配范围只限当前 `candidate_ids` 与当前仍可删除任务的交集。
4. 多候选时将 `candidate_ids` 收窄为本次匹配结果；零候选时保留原范围。
5. 不支持序号、近似编辑距离、分词推断或模型语义匹配。

### 确认与取消

- 待确认阶段只有去除首尾空白后完全等于 `确认删除` 才执行。
- `确认`、`确定`、`删除` 等返回安全提示并保持待确认状态。
- `取消`、`取消删除` 清除状态。
- 成功确认、复核失败或过期都会清除状态；重复确认返回“当前没有待确认删除的任务”。

### 过期

- 状态 TTL 为 600 秒。
- 用户在选择/消歧阶段产生有效匹配后刷新 TTL。
- 已过期状态先清除；若当前消息是新的删除发起指令则直接创建新流程，否则回复已过期。
- 状态仅在内存中存在，重启自然失效。

## 模块设计

### 删除对话状态机

**职责：** 删除意图、短期状态、关键词消歧、确认/取消、错误文案。

**依赖：** `TaskService`、删除展示函数、单调时钟。

### 任务服务与仓储

**职责：** 用户作用域的可删除任务查询，以及确认时的原子状态转换。

**依赖：** `TasksRepo`、现有 Store 事务与用户过滤约束。

### Gateway 渠道接入

**职责：** 将飞书/Web 的稳定 session key 传给任务对话流程；继续复用已有 transcript 记录。

**依赖：** 身份解析、session routing、`record_session_exchange`。

### 调度收敛

**职责：** 不新增逻辑；复用 `SchedulerLoop._finish_draining` 取消 pending execution 并转为 deleted。

## 模块交互

### 发起与消歧

1. 飞书消息解析为规范用户和 session key。
2. 删除状态机按该 scope 查询可删除任务并保存候选 ID。
3. 用户输入关键词，状态机重新读取可删除任务并与候选 ID求交。
4. 多结果时收窄候选；唯一结果时保存 selected task ID并输出确认摘要。

### 确认删除

1. 状态机验证 scope、TTL 和确认短语。
2. 调用 `TaskService.confirm_delete(user_id, selected_task_id)`。
3. Repository 在一条条件 UPDATE 中校验所有权与状态并转为 `draining`。
4. 无论成功或失败都清除待确认状态。
5. 调度器下一次 tick 取消 pending execution；无 running execution 时转为 `deleted`。

### transcript

删除状态机返回的每条文本均沿用 Gateway 现有确定性回复路径，因此发起、关键词、消歧、确认/取消及结果都会按 user/assistant 顺序进入同一个 session transcript，无需让业务状态机直接操作文件。

## 文件组织

```text
backend/src/watchlight/
├── scheduler/
│   ├── nl.py                  — 组合删除流程并按会话划分创建状态
│   ├── nl_delete.py           — 新建删除意图与短期状态机
│   ├── presentation.py        — 删除候选与确认摘要格式化
│   └── service.py             — 可删除列表与确认删除业务接口
├── storage/repos/tasks.py     — 原子 active|paused → draining
├── gateway/
│   ├── boot.py                — 飞书传入 session_key
│   └── methods/sessions.py    — Web 传入 session_key
└── agents/system_prompt/builder.py — 声明删除必须走平台二次确认流程

tests/watchlight/
├── test_channels_nl_delete.py — 新建关键词、消歧、TTL、取消、复核、隔离测试
├── test_channels_identity.py  — 飞书完整删除流程与 transcript
├── test_gateway_methods.py    — Web 删除流程会话隔离
├── test_storage_repos_tasks.py— 原子状态转换与所有权
├── test_scheduler_loop.py     — draining 收敛且不再排期
└── test_system_prompt.py      — 删除安全规则
```

## 技术决策

| 决策点 | 选择 | 理由 |
|---|---|---|
| 写操作执行者 | 确定性状态机 | 删除不应依赖模型选工具或自由生成参数 |
| 候选匹配 | casefold 名称包含匹配 + 完整 ID精确匹配 | 符合用户选择，同时行为稳定可测试 |
| 多候选处理 | 保存并逐轮收窄候选 ID集合 | 防止后续关键词跳到最初列表之外的任务 |
| 确认短语 | 仅 `确认删除` | 与创建确认区分，降低误操作风险 |
| 状态作用域 | 用户 + 渠道 + session key | 阻止跨用户和跨会话确认 |
| TTL | 进程内 10 分钟单调时钟 | 短期安全状态无需持久化，重启自动失效 |
| 最终状态更新 | Repository 原子条件 UPDATE | 消除确认复核与更新之间的竞态 |
| REST 兼容 | 保留现有 `TaskService.delete` | 新安全接口只供对话确认流程使用 |
| 模型权限 | 不注册删除写工具 | 不扩大远程消息工具攻击面 |

## Spec 覆盖

| Spec | 设计归属 |
|---|---|
| F1–F7 | `NaturalLanguageDeleteFlow`、删除展示函数 |
| F8 | scope key、TTL、内存状态 |
| F9 | `confirm_delete`、`begin_draining` 原子更新 |
| F10 | 现有 SchedulerLoop 收敛 |
| F11–F12 | Gateway session key 传递与既有 transcript 路径 |

所有功能需求均有明确实现归属；删除状态机只依赖业务服务，Gateway 只负责身份、会话与记录，不形成反向依赖。
