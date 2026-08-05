# 关注任务查询一致性修复 Checklist

> 每项均通过运行测试或观察持久化结果验证。实现完成后记录实际证据，再标记通过。

## 验收结果（2026-08-03）

- [x] AC1–AC6 全部通过；飞书创建、确认、查询端到端用例返回真实 active 任务，并将三轮问答写入同一 transcript。
- [x] 确定性查询覆盖多任务、空列表、数据库异常及创建意图防误判。
- [x] `watch_tasks_list` 通过 `ToolContext.user_id` 隔离用户，缺少身份时失败关闭，输入 schema 不接受用户身份参数。
- [x] Embedded Runtime 工具循环验证规范身份能够到达任务工具并返回真实数据库结果。
- [x] Web 与飞书普通模型路径均验证规范用户身份传播；确定性路径不调用模型且不产生 token。
- [x] 全量测试：`pytest tests/watchlight -q` → `63 passed`。
- [x] 静态检查：`ruff check backend/src/watchlight tests/watchlight` → `All checks passed!`。
- [x] 类型检查：`mypy backend/src/watchlight` → `Success: no issues found in 296 source files`。

以下条目为验收设计明细；其行为已由上述自动化测试、静态检查和端到端场景共同覆盖。

## 确定性任务查询

- [x] “目前创建了哪些任务”“查看已创建任务”“我之前创建的任务”均直接返回持久化任务列表。（验证：运行 `python -m pytest tests/watchlight/test_channels_nl_create.py -q`，对应参数化用例通过）
- [x] “创建关注任务”仍进入创建流程，不被列表意图误判。（验证：运行自然语言创建测试，首次回复仍为补充或确认提示）
- [x] 有一个 active 任务时，回复包含关注目标、启用状态、执行频率和通知渠道。（验证：构造任务后查询，断言四类字段均出现）
- [x] 同一用户有多个任务时全部列出，且每项仅出现一次。（验证：创建两个不同目标后查询并分别计数）
- [x] 用户没有任务时明确回复“当前没有关注任务”。（验证：空数据库用户查询用例通过）
- [x] 数据库查询异常时明确回复暂时无法查询，不包含“当前没有关注任务”或“系统中没有任务”。（验证：模拟 `TaskService.list` 抛出异常）

## 任务视图与只读性

- [x] 确定性回复和模型工具使用相同的人类可读状态、频率与渠道名称。（验证：对同一任务比较格式化回复和工具 `TaskView` 标签）
- [x] `watch_tasks_list` 输出仅包含批准的只读字段，不包含 `user_id`、原始 JSON、版本或执行计划字段。（验证：断言工具返回 key 集合）
- [x] 执行列表查询前后，任务数量、任务版本、状态及 execution 记录完全不变。（验证：查询前后读取数据库并比较）
- [x] 无效通知策略数据不会泄漏或导致整个列表失败，而是安全展示为空渠道。（验证：格式化模块异常数据用例通过）

## 身份隔离与工具安全

- [x] `watch_tasks_list` 的输入 schema 不接受 `user_id`。（验证：读取工具 catalog，断言 properties 中不存在用户身份字段）
- [x] 工具只使用 `ToolContext.user_id` 查询当前用户任务。（验证：两个用户各建一个任务，分别调用工具只返回各自目标）
- [x] 缺少 `ToolContext.user_id` 时工具执行失败，不返回全局或空任务列表。（验证：无身份上下文调用用例通过）
- [x] 模型无法通过额外参数读取另一用户任务。（验证：传入伪造 `user_id` 参数后结果仍按上下文用户，或因 schema/额外参数策略拒绝）
- [x] 飞书和 Web 普通模型路径均把身份注册表解析出的规范用户身份传入运行时。（验证：mock runtime 捕获 `AgentRunRequest.metadata.userId`）

## 工具装配与权限

- [x] Watchlight 业务服务成功启动后，Gateway 工具目录包含 `watch_tasks_list`。（验证：bootstrap 集成测试读取 registry）
- [x] messaging profile 允许 `watch_tasks_list`。（验证：`ToolPolicy(profile="messaging").is_allowed("watch_tasks_list")` 为真）
- [x] messaging profile 仍拒绝 Shell、文件写入、编辑和补丁工具。（验证：现有 deny 集合行为断言通过）
- [x] 未装配业务 Store 的 Gateway 不暴露一个无法工作的任务工具。（验证：仅创建 `GatewayRuntime` 时 catalog 不包含该动态工具）

## 会话历史一致性

- [x] 飞书自然语言创建、补充、确认、列表查询及每次对应回复按顺序写入同一个 transcript。（验证：完整流程后读取 session JSONL，角色严格 user/assistant 交替）
- [x] Web 确定性任务回复同样写入调用方指定的 session。（验证：Web session 发送后读取对应 transcript）
- [x] 每条确定性输入和回复只记录一次。（验证：按消息文本计数均为 1）
- [x] 确定性路径不调用模型且 token 用量不增加。（验证：mock `run_agent_for_session` 未调用，返回 token 为 0）
- [x] 未命中确定性路径时继续调用模型，并由普通模型流程负责记录一次问答。（验证：普通消息集成测试通过且 transcript 无重复）

## 模型真实性约束

- [x] System Prompt 明确任务存在性只能依据 `watch_tasks_list` 或平台确定性任务查询结果。（验证：`python -m pytest tests/watchlight/test_system_prompt.py -q`）
- [x] System Prompt 明确会话列表、记忆搜索和聊天历史不能代替任务数据库查询。（验证：提示文本断言通过）
- [x] System Prompt 明确工具查询失败必须报告失败，不能回答“没有任务”。（验证：提示文本断言通过）

## 集成与回归

- [x] 原自然语言任务创建、两轮补充和确认启用行为保持不变。（验证：`python -m pytest tests/watchlight/test_channels_nl_create.py -q`）
- [x] 原身份注册、绑定和用户数据隔离行为保持不变。（验证：`python -m pytest tests/watchlight/test_identity.py tests/watchlight/test_channels_identity.py tests/watchlight/test_storage_repo_isolation.py -q`）
- [x] 原任务存储、版本与软删除行为保持不变。（验证：`python -m pytest tests/watchlight/test_storage_repos_tasks.py tests/watchlight/test_scheduler_service.py -q`）
- [x] 原调度和执行计划行为保持不变。（验证：`python -m pytest tests/watchlight/test_scheduler_loop.py tests/watchlight/test_e2e.py -q`）
- [x] 全部 Watchlight 后端测试通过。（验证：`python -m pytest tests/watchlight -q`）
- [x] Ruff 检查无本次改动引入的问题。（验证：`python -m ruff check backend/src/watchlight tests/watchlight`）
- [x] mypy 检查无本次改动引入的类型错误。（验证：`python -m mypy backend/src/watchlight`）

## 端到端场景

- [x] 场景 1——飞书创建后查询：用户发送完整关注任务描述，收到确认摘要；回复“确认”，收到“已创建并启用”；再问“目前创建了哪些任务”，看到同一任务的目标、启用状态、每天执行和飞书通知。（验证：飞书入站 Gateway 集成测试，不调用真实外部 API）
- [x] 场景 2——多用户隔离：飞书用户 A 与用户 B 分别创建任务；A 的确定性查询和工具查询都只出现 A 的任务，B 同理。（验证：双身份 Store/Gateway 集成测试）
- [x] 场景 3——失败不冒充空列表：关闭或模拟任务存储异常后查询，回复为查询失败；使用真实空用户查询，回复为空状态，两种文案可明确区分。（验证：异常与空状态对照测试）
- [x] 场景 4——长尾问法：一条未命中固定列表规则但表达任务回顾意图的消息进入模型；模型可见 `watch_tasks_list`，工具用规范用户身份返回真实任务。（验证：Embedded Runtime 工具上下文集成测试或等价的工具循环 mock）

## 验收标准映射

| 验收标准 | Checklist 覆盖 |
|---|---|
| AC1 | 确定性任务查询、端到端场景 1 |
| AC2 | 多任务、空状态、异常状态、端到端场景 3 |
| AC3 | 身份隔离与工具安全、端到端场景 2 |
| AC4 | 工具装配、ToolContext、端到端场景 4 |
| AC5 | 会话历史一致性、端到端场景 1 |
| AC6 | 集成与回归全部检查 |
