# 飞书自然语言删除关注任务 Tasks

## 文件清单

| 操作 | 文件 | 职责 |
|---|---|---|
| 新建 | `backend/src/watchlight/scheduler/nl_delete.py` | 删除意图、关键词消歧、TTL、确认与取消状态机 |
| 修改 | `backend/src/watchlight/scheduler/nl.py` | 组合删除状态机并按 session 划分对话状态 |
| 修改 | `backend/src/watchlight/scheduler/presentation.py` | 删除候选列表与确认摘要格式化 |
| 修改 | `backend/src/watchlight/scheduler/service.py` | 可删除任务列表与确认删除接口 |
| 修改 | `backend/src/watchlight/storage/repos/tasks.py` | 原子 `active|paused → draining` |
| 修改 | `backend/src/watchlight/gateway/boot.py` | 飞书向任务流程传入稳定 session key |
| 修改 | `backend/src/watchlight/gateway/methods/sessions.py` | Web 向任务流程传入 session key |
| 修改 | `backend/src/watchlight/agents/system_prompt/builder.py` | 声明删除必须经过平台二次确认 |
| 新建 | `tests/watchlight/test_channels_nl_delete.py` | 删除状态机安全与隔离测试 |
| 修改 | `tests/watchlight/test_channels_identity.py` | 飞书删除端到端与 transcript 测试 |
| 修改 | `tests/watchlight/test_gateway_methods.py` | Web 会话作用域测试 |
| 修改 | `tests/watchlight/test_storage_repos_tasks.py` | 原子转换与跨用户隔离测试 |
| 修改 | `tests/watchlight/test_scheduler_loop.py` | 删除收敛与停止排期测试 |
| 修改 | `tests/watchlight/test_system_prompt.py` | 删除确认安全规则测试 |

## T1：实现原子删除业务能力

**文件：** `backend/src/watchlight/storage/repos/tasks.py`、`backend/src/watchlight/scheduler/service.py`、`tests/watchlight/test_storage_repos_tasks.py`

**依赖：** 无

**步骤：**

1. 在用户作用域 repository 中实现 `begin_draining(task_id)`。
2. 使用单条条件 UPDATE，仅允许 `active|paused` 转为 `draining`，并检查受影响行数。
3. 为 `TaskService` 增加 `list_deletable(user_id)`，过滤 `active|paused`。
4. 为 `TaskService` 增加 `confirm_delete(user_id, task_id)`，失败返回 `None`。
5. 保持现有 `delete` 方法不变，确保 REST API 兼容。
6. 测试 active、paused 成功，draining、deleted、不存在和其他用户任务失败。

**验证：** `pytest tests/watchlight/test_storage_repos_tasks.py tests/watchlight/test_scheduler_service.py -q` 全部通过。

## T2：实现删除候选和确认展示

**文件：** `backend/src/watchlight/scheduler/presentation.py`

**依赖：** T1

**步骤：**

1. 实现删除候选列表格式化，逐项展示目标、状态标签、原始状态和完整 task ID。
2. 区分首次列表与已收窄的消歧列表标题。
3. 明确提示仅接受名称关键词或完整 task ID，不提示序号选择。
4. 实现唯一候选确认摘要，说明停止后续执行与通知的影响。
5. 确认摘要只提示“确认删除”与“取消”。

**验证：** 在删除状态机测试中断言候选、完整 ID、状态及确认影响文案。

## T3：实现删除对话状态机

**文件：** `backend/src/watchlight/scheduler/nl_delete.py`、`tests/watchlight/test_channels_nl_delete.py`

**依赖：** T1、T2

**步骤：**

1. 定义 `DeleteConversation` 和按用户、渠道、会话组成的 scope key。
2. 实现明确删除命令识别，并排除“如何删除任务”等咨询问法。
3. 首次发起时查询可删除任务；为空时直接提示且不保存状态。
4. 实现完整 ID精确匹配和名称 `casefold` 包含匹配。
5. 零匹配保留候选；多匹配收窄候选；唯一匹配进入待确认。
6. 实现仅“确认删除”执行、其他确认文本安全拒绝、取消清理。
7. 实现 600 秒 TTL、有效消歧刷新 TTL、过期和重新发起行为。
8. 确认成功、复核失败或过期后清理状态，保证重复确认安全。

**验证：** `pytest tests/watchlight/test_channels_nl_delete.py -q`，覆盖意图、匹配、逐轮消歧、ID、确认、取消、TTL、重复确认和复核失败。

## T4：组合现有任务对话流程

**文件：** `backend/src/watchlight/scheduler/nl.py`、`tests/watchlight/test_channels_nl_create.py`、`tests/watchlight/test_channels_nl_delete.py`

**依赖：** T3

**步骤：**

1. `NaturalLanguageTaskFlow` 初始化删除状态机。
2. 扩展 `handle` 接收可选 `conversation_id` 与测试用 `now`。
3. 删除流程优先处理；返回 `None` 时继续任务查询和创建流程。
4. 将创建 pending key 扩展为用户、渠道、会话三元组。
5. 保证旧调用不传 conversation ID 时行为不变。
6. 验证删除确认与创建“确认”互不混淆。

**验证：** `pytest tests/watchlight/test_channels_nl_create.py tests/watchlight/test_channels_nl_delete.py -q` 全部通过。

## T5：接入飞书和 Web 会话作用域

**文件：** `backend/src/watchlight/gateway/boot.py`、`backend/src/watchlight/gateway/methods/sessions.py`、`tests/watchlight/test_gateway_methods.py`

**依赖：** T4

**步骤：**

1. 飞书调用任务流程时传入已解析的 `session_key`。
2. Web 调用任务流程时传入请求的 `sessionKey`。
3. 保持现有确定性回复 `record_session_exchange` 行为不变。
4. 验证同一用户在会话 A 发起后，不能在会话 B确认或取消 A 的删除。
5. 验证 Web 与飞书使用相同的删除状态机语义。

**验证：** `pytest tests/watchlight/test_gateway_methods.py tests/watchlight/test_channels_identity.py -q` 全部通过。

## T6：验证飞书完整删除与调度收敛

**文件：** `tests/watchlight/test_channels_identity.py`、`tests/watchlight/test_scheduler_loop.py`

**依赖：** T1–T5

**步骤：**

1. 构造飞书用户及两个名称有公共关键词的 active 任务。
2. 走“删除任务 → 公共关键词 → 更精确关键词 → 确认删除”完整流程。
3. 断言模型从未被调用，每轮回复均通过确定性通道发送。
4. 读取 transcript，验证四轮 user/assistant 顺序且每条只出现一次。
5. 确认目标进入 `draining`，非目标仍为 `active`。
6. 执行 Scheduler tick，验证 pending execution 取消、任务进入 `deleted`、普通列表不再返回。

**验证：** `pytest tests/watchlight/test_channels_identity.py tests/watchlight/test_scheduler_loop.py -q` 全部通过。

## T7：强化模型安全提示且不扩大工具权限

**文件：** `backend/src/watchlight/agents/system_prompt/builder.py`、`tests/watchlight/test_system_prompt.py`、`tests/watchlight/test_boot.py`

**依赖：** T4

**步骤：**

1. System Prompt 明确删除必须使用平台确定性流程并取得“确认删除”。
2. 明确模型不得凭普通确认文本声称已删除任务。
3. 验证工具目录未新增 `watch_tasks_delete` 或其他任务写工具。
4. 验证 messaging profile 的现有安全拒绝规则保持不变。

**验证：** `pytest tests/watchlight/test_system_prompt.py tests/watchlight/test_boot.py -q` 全部通过。

## T8：全量回归与验收

**文件：** 上述全部文件

**依赖：** T1–T7

**步骤：**

1. 执行删除状态机所有安全边界测试。
2. 执行飞书/Web 端到端测试及调度收敛测试。
3. 执行全部 Watchlight 后端测试。
4. 执行 Ruff 与 mypy。
5. 将真实结果回填 `checklist.md`。

**验证：**

```powershell
pytest tests/watchlight -q
ruff check backend/src/watchlight tests/watchlight
mypy backend/src/watchlight
```

期望全部测试通过、Ruff 无问题、mypy 无类型错误。

## 执行顺序

```text
T1 → T2 → T3 → T4 → T5 → T6 → T8
                   └──────→ T7 ─┘
```

每项验证通过后才进入依赖它的下一项。
