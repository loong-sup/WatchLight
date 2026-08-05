# 关注任务查询一致性修复 Tasks

## 文件清单

| 操作 | 文件 | 职责 |
|---|---|---|
| 新建 | `backend/src/watchlight/scheduler/presentation.py` | 任务只读视图、频率/状态/渠道格式化、列表回复 |
| 修改 | `backend/src/watchlight/scheduler/service.py` | 增加按用户列出未删除任务的业务入口 |
| 修改 | `backend/src/watchlight/scheduler/nl.py` | 识别常见列表意图并执行确定性查询 |
| 新建 | `backend/src/watchlight/tools/builtin/watch_tasks.py` | 按工具上下文身份查询任务的只读工具 |
| 修改 | `backend/src/watchlight/tools/types.py` | `ToolContext` 增加规范用户身份 |
| 修改 | `backend/src/watchlight/tools/policy.py` | messaging profile 允许任务只读工具 |
| 修改 | `backend/src/watchlight/agents/runtime/embedded/runner.py` | 将请求 metadata 身份注入工具上下文 |
| 修改 | `backend/src/watchlight/agents/system_prompt/builder.py` | 约束模型只能依据真实任务查询结果判断任务存在性 |
| 修改 | `backend/src/watchlight/gateway/boot.py` | 传播用户身份；增加确定性问答 transcript 记录接口；接入飞书 |
| 修改 | `backend/src/watchlight/gateway/boot_watchshed.py` | 业务 Store 就绪后注册任务只读工具 |
| 修改 | `backend/src/watchlight/gateway/methods/sessions.py` | Web 路径传播身份并记录确定性问答 |
| 修改 | `tests/watchlight/test_channels_nl_create.py` | 列表意图、展示、空状态和异常测试 |
| 新建 | `tests/watchlight/test_watch_tasks_tool.py` | 工具输出、缺失身份和跨用户隔离测试 |
| 修改 | `tests/watchlight/test_channels_identity.py` | 飞书确定性回复 transcript 与模型身份传播测试 |
| 修改 | `tests/watchlight/test_gateway_methods.py` | Web 确定性回复 transcript 测试 |
| 修改 | `tests/watchlight/test_system_prompt.py` | 任务查询真实性约束测试 |
| 修改 | `tests/watchlight/test_boot.py` | 动态工具注册和 messaging 权限测试 |

## T1：建立统一任务只读视图

**文件：** `backend/src/watchlight/scheduler/presentation.py`、`backend/src/watchlight/scheduler/service.py`

**依赖：** 无

**步骤：**

1. 定义 `TaskView`，仅包含 task ID、目标、原始/人类可读状态、原始/人类可读频率、原始/人类可读通知渠道。
2. 实现任务存储行到 `TaskView` 的转换，安全解析通知策略 JSON；无效 JSON 使用空渠道展示，不抛出用户数据内容。
3. 实现空列表和多任务的 Markdown 文本格式化。
4. 将 `nl.py` 中已有频率与渠道显示逻辑迁入展示模块，并保留确认摘要的既有输出语义。
5. 为 `TaskService` 增加 `list(user_id)`，内部只调用用户作用域的 `TasksRepo.list()`。

**验证：** `python -m pytest tests/watchlight/test_scheduler_service.py tests/watchlight/test_storage_repos_tasks.py -q`，期望全部通过。

## T2：增加确定性任务列表意图

**文件：** `backend/src/watchlight/scheduler/nl.py`、`tests/watchlight/test_channels_nl_create.py`

**依赖：** T1

**步骤：**

1. 实现 `is_task_list_intent(text)`，同时要求任务语义与查询/回顾语义。
2. 在创建流程判断之前处理列表意图，调用 `TaskService.list(user_id)` 并使用统一格式化函数回复。
3. 覆盖“目前创建了哪些任务”“查看已创建任务”“我之前创建的任务”等问法。
4. 验证“创建关注任务”不会误入列表查询。
5. 捕获数据库访问异常并返回明确查询失败文案，不返回空列表文案。

**验证：** `python -m pytest tests/watchlight/test_channels_nl_create.py -q`，期望列表、多任务、空状态、异常和原创建流程测试全部通过。

## T3：实现并装配只读任务工具

**文件：** `backend/src/watchlight/tools/builtin/watch_tasks.py`、`backend/src/watchlight/tools/policy.py`、`backend/src/watchlight/gateway/boot_watchshed.py`、`tests/watchlight/test_watch_tasks_tool.py`、`tests/watchlight/test_boot.py`

**依赖：** T1

**步骤：**

1. 新建 `create_watch_tasks_list_tool(store)`，工具 schema 不包含 `user_id` 或其他用户选择参数。
2. handler 要求 `ToolContext.user_id` 非空，按该身份调用任务服务并返回 `{count, tasks}`。
3. 使用统一 `TaskView` 生成结构化输出，不暴露 `user_id`、原始 JSON 或版本字段。
4. 将 `watch_tasks_list` 加入 messaging profile 的 allow 列表，不增加任何写工具权限。
5. 在 `bootstrap_watchlight` 完成 Store 和服务创建后，把工具注册到 Gateway 的共享 registry。

**验证：** `python -m pytest tests/watchlight/test_watch_tasks_tool.py tests/watchlight/test_boot.py -q`，期望工具身份、隔离、输出 schema、装配和权限测试全部通过。

## T4：贯通规范用户身份到工具上下文

**文件：** `backend/src/watchlight/tools/types.py`、`backend/src/watchlight/gateway/boot.py`、`backend/src/watchlight/agents/runtime/embedded/runner.py`

**依赖：** T3

**步骤：**

1. 给 `ToolContext` 增加可选 `user_id` 字段。
2. 给 `GatewayRuntime.run_agent_for_session` 增加仅供内部调用的可选 `user_id` 参数，并写入 `AgentRunRequest.metadata["userId"]`。
3. Embedded Runtime 从 metadata 读取 `userId`，构建 `ToolContext.user_id`。
4. 飞书路径调用模型时传入刚由 `IdentityRegistry` 解析的规范身份。
5. 保持没有业务身份的旧调用兼容，但此时任务工具必须拒绝执行。

**验证：** 新增的工具上下文测试中观察 handler 使用网关注入身份；运行 `python -m pytest tests/watchlight/test_watch_tasks_tool.py tests/watchlight/test_channels_identity.py -q` 全部通过。

## T5：增加确定性问答会话记录接口

**文件：** `backend/src/watchlight/gateway/boot.py`

**依赖：** 无

**步骤：**

1. 实现 `record_session_exchange`，不存在 session 时创建，存在时复用。
2. 按 user、assistant 顺序写入当前毫秒时间戳的 transcript。
3. 合并 channel 与可选 route patch，更新 session 并保存索引。
4. 确保此接口不调用模型、不产生 token 用量，也不改变普通 `run_agent_for_session` 的既有记录逻辑。

**验证：** 增加一个隔离的 session/transcript 单元测试，调用一次后读取到恰好两条且角色、文本、顺序正确。

## T6：接入飞书确定性回复记录

**文件：** `backend/src/watchlight/gateway/boot.py`、`tests/watchlight/test_channels_identity.py`

**依赖：** T2、T4、T5

**步骤：**

1. 飞书入站在自然语言任务流程前解析稳定 `session_key` 和最近路由 patch。
2. `nl_tasks.handle` 返回确定性回复时，先调用 `record_session_exchange`，再发送渠道回复并结束。
3. 未命中确定性流程时继续复用同一 session key 进入模型，并传递规范 `user_id`。
4. 验证确定性路径不会调用模型，模型路径不会重复记录消息。

**验证：** `python -m pytest tests/watchlight/test_channels_identity.py -q`，期望飞书创建/列表回复落盘、身份传播与现有首次注册行为全部通过。

## T7：接入 Web 确定性回复记录与身份传播

**文件：** `backend/src/watchlight/gateway/methods/sessions.py`、`tests/watchlight/test_gateway_methods.py`

**依赖：** T2、T4、T5

**步骤：**

1. Web 的 `nl_tasks.handle` 返回确定性回复时调用 `record_session_exchange`。
2. 普通模型路径将已解析的规范 `user_id` 传给 `run_agent_for_session`。
3. 保留现有 text delta 和 complete 事件行为。
4. 验证 Web 确定性问答在 transcript 中只出现一次。

**验证：** `python -m pytest tests/watchlight/test_gateway_methods.py -q`，期望 REST 身份隔离与 Web 会话记录测试全部通过。

## T8：强化模型任务查询约束

**文件：** `backend/src/watchlight/agents/system_prompt/builder.py`、`tests/watchlight/test_system_prompt.py`

**依赖：** T3

**步骤：**

1. 明确任务存在性只能以 `watch_tasks_list` 或平台确定性任务查询结果为依据。
2. 明确会话列表、记忆搜索和聊天历史不能代替任务数据库查询。
3. 明确工具失败时说明失败，不得回答“没有任务”。
4. 保持原有身份、来源真实性和任务确认规则不变。

**验证：** `python -m pytest tests/watchlight/test_system_prompt.py -q`，期望新增约束与原提示兼容测试全部通过。

## T9：端到端与回归验收

**文件：** 上述全部实现和测试文件

**依赖：** T1–T8

**步骤：**

1. 构造飞书用户创建、补充、确认、查询列表的完整流程，断言返回真实 active 任务。
2. 构造第二用户并验证确定性查询与工具查询均不串数据。
3. 验证数据库异常与身份缺失分别返回失败而非空状态。
4. 运行全部后端测试。
5. 运行 Ruff 和 mypy；仅修复本次改动引入的问题，不改写无关用户代码。

**验证：**

```powershell
python -m pytest tests/watchlight -q
python -m ruff check backend/src/watchlight tests/watchlight
python -m mypy backend/src/watchlight
```

期望测试全部通过，Ruff 无新增问题，mypy 无新增类型错误。

## 执行顺序

```text
T1 ─→ T2 ───────────┐
 │                  ├─→ T6 ─┐
 └─→ T3 ─→ T4 ─────┤       │
          │         └─→ T7 ─┼─→ T9
          └─→ T8            │
T5 ─────────────────────────┘
```

T1 与 T5 可先后独立执行；其余任务按图中依赖推进。每项验证通过后才进入依赖它的下一项。
