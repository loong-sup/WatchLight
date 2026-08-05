# Watchlight MVP Plan

> 输入：已批准的 `docs/spec.md` v0.4
> 输出：本文件被批准后供 `task.md` 拆解
> 约束：本文件不得引入 spec 未提及的能力；方法名、类名、表结构在本层定义

## 架构概览

Watchlight 在现有 gateway(channels/gateway/sessions/tools/extensions)之上新增 7 个业务子系统,严格按 spec 4.3 的依赖方向单向流动:

```
                 ┌──────────────┐
                 │   identity   │  解析渠道身份 → user_id；绑定/解绑确认
                 └──────┬───────┘
                        │ user_id
                        ▼
                 ┌──────────────┐         ┌────────────┐
                 │   scheduler  │ ◀────── │  feedback  │  偏好回喂给分析层
                 │ (任务+计划)   │         └─────┬──────┘
                 └──────┬───────┘             │
                        │ pending Execution   │
                        ▼                     │
                 ┌──────────────┐             │
                 │   collector  │             │
                 │ (采集+快照)  │             │
                 └──────┬───────┘             │
                        │ SourceHit/Snapshot │
                        ▼                     │
                 ┌──────────────┐ ◀───────────┘
                 │   analyzer   │
                 │ (变化+信号+   │
                 │  简报)       │
                 └──────┬───────┘
                        │ sendable Brief
                        ▼
                 ┌──────────────┐
                 │   notifier   │  渠道选择+免打扰+重试
                 └──────┬───────┘
                        │ Delivery
                        ▼
                 ┌──────────────┐
                 │  observing   │  旁路打点,所有层产出事件
                 └──────────────┘
```

现有 `channels/`(入站消息适配)、`gateway/`(HTTP/WS)、`tools/builtin/web_fetch`、`tools/builtin/web_search`、`extensions/*` provider、`tools/sandbox/policy` 作为基础能力复用,但**不在它们里面塞业务逻辑**:identity 调用 channels 解析身份后只依赖 user_id 进入 scheduler 之后链路;collector 复用 web_fetch/web_search 的 provider 抽象而不直接调用其工具实现。

新增包结构:

```
backend/src/watchlight/
├── identity/         # F1
├── scheduler/        # F2 F4 F13
├── collector/        # F3 F5 N9 N11
├── analyzer/         # F6 F7 F8
├── notifier/         # F9 F13
├── feedback/         # F10
├── observing/        # F11 N4 N8
└── storage/          # SQLite 仓储 + 迁移 + 隔离(被所有上述层依赖)
```

被允许的依赖方向(必须单向,不得反向):
- storage → 仅 stdlib
- identity → storage, channels(只读解析)
- scheduler → storage, identity
- collector → storage, identity, tools/sandbox/policy(只读), extensions(模型/搜索的 provider 接口)
- analyzer → storage, identity, extensions, feedback(只读偏好)
- notifier → storage, identity, channels(只写出站), observing(只写事件)
- feedback → storage, identity
- observing → storage(只写事件)

## 核心数据结构

所有时间字段 `UTC POSIX 秒`(int),展示层再渲染时区(N10)。所有 `*_id` 为 `TEXT` UUIDv7(时间有序,便于按时间切片)。schema 版本由 `schema_version` 表管理,启动迁移幂等。

### WatchTask(`watch_tasks`)

| 列 | 类型 | 说明 |
|----|------|------|
| task_id | TEXT PK | UUIDv7 |
| user_id | TEXT | FK identity.users |
| target | TEXT | 用户自然语言目标 |
| source_scope_json | TEXT | `{keywords:[...], urls:[...], include_domains:[...], exclude_domains:[...]}` |
| trigger_condition_json | TEXT | `{must_contain:[...], must_not_contain:[...], importance_min:0..1}` |
| frequency_seconds | INT | 900..604800,15min..7day |
| notification_policy_json | TEXT | `{channels:[...], immediate:bool, digest_cron:..., do_not_disturb:{from,to,tz}}` |
| status | TEXT | `active\|paused\|deleted\|draining` (4.1) |
| version | INT | 单调递增 |
| current_version_id | TEXT | 指向当前生效的历史版本 |
| created_at | INT | UTC 秒 |
| updated_at | INT | UTC 秒 |

历史版本写入追加表 `watch_task_versions(task_id, version, modifier_user_id, modified_at, snapshot_json)`,任务每次修改插入新 version 行(N14)。

### Execution(`executions`)

| 列 | 类型 | 说明 |
|----|------|------|
| execution_id | TEXT PK | |
| task_id | TEXT | |
| task_version_id | TEXT | 本次执行依据的条件版本(N14) |
| scheduled_at | INT | |
| started_at | INT NULL | |
| ended_at | INT NULL | |
| status | TEXT | `pending\|running\|succeeded\|partial\|failed\|cancelled\|timed_out\|recovered` |
| source_count | INT | |
| change_count | INT | |
| signal_count | INT | |
| delivery_count | INT | |
| failure_summary | TEXT | 脱敏后的失败分类摘要 |
| triggered_by | TEXT | `cron\|manual\|bootstrap` |
| heartbeat_at | INT NULL | 用于 running 超时收敛(F12) |

### SourceHit(`source_hits`)

| 列 | 类型 | 说明 |
|----|------|------|
| hit_id | TEXT PK | |
| execution_id | TEXT | |
| source_url | TEXT | |
| fetched_at | INT NULL | |
| status | TEXT | `ok\|unchanged\|changed\|unreachable\|unparseable\|blocked` |
| http_status | INT NULL | |
| snapshot_id | TEXT NULL | |
| error_code | TEXT NULL | spec N12 分类码 |
| retry_count | INT | |
| robots_disallowed | INT | 0/1 |

### Snapshot(`snapshots`)

| 列 | 类型 | 说明 |
|----|------|------|
| snapshot_id | TEXT PK | |
| source_url | TEXT | |
| captured_at | INT | |
| content_hash | TEXT | SHA256 of normalized content |
| raw_ref | TEXT | 原始响应 blob 的存储引用 |
| normalized_ref | TEXT | 归一化正文引用 |
| previous_snapshot_id | TEXT NULL | |

raw/normalized blob 落入 `snapshot_blobs(blob_id, kind, bytes)`;表只存引用,便于追加写(N14)。

### Change(`changes`)

| 列 | 类型 | 说明 |
|----|------|------|
| change_id | TEXT PK | |
| snapshot_id | TEXT | |
| previous_snapshot_id | TEXT | |
| change_type | TEXT | `added\|removed\|modified` |
| evidence_ref | TEXT | 指向 normalized blob 偏移 |
| uncertainty_level | TEXT | `high\|medium\|low` |

### Signal(`signals`)

| 列 | 类型 | 说明 |
|----|------|------|
| signal_id | TEXT PK | |
| execution_id | TEXT | |
| task_id | TEXT | |
| change_ids_json | TEXT | |
| source_urls_json | TEXT | |
| captured_at | INT | |
| relevance | REAL | 0..1 |
| importance | REAL | 0..1 |
| novelty | REAL | 0..1 |
| source_credibility | REAL | 0..1 |
| uncertainty_level | TEXT | |
| status | TEXT | `proposed\|suppressed\|notified\|deduped\|expired` |
| dedup_key | TEXT | 内容指纹 + task_id + 72h 窗口(F9) |
| status_history_json | TEXT | 状态流转追加写(AC18 要求可追溯) |

### Brief(`briefs`)

| 列 | 类型 | 说明 |
|----|------|------|
| brief_id | TEXT PK | |
| signal_ids_json | TEXT | |
| facts_json | TEXT | |
| inferences_json | TEXT | |
| next_steps_json | TEXT | |
| source_refs_json | TEXT | |
| captured_at | INT | |
| uncertainty_level | TEXT | |
| sendable | INT | 0/1 |

### Delivery(`deliveries`)

| 列 | 类型 | 说明 |
|----|------|------|
| delivery_id | TEXT PK | |
| signal_id | TEXT | |
| brief_id | TEXT | |
| channel_key | TEXT | web/feishu |
| user_id | TEXT | |
| status | TEXT | `queued\|sending\|delivered\|retry\|failed\|deferred\|suppressed` |
| attempts | INT | |
| last_error | TEXT | 脱敏 |
| scheduled_send_at | INT | 免打扰延迟目标时间 |
| sent_at | INT NULL | |

### Feedback / Preferences

`feedbacks(feedback_id, delivery_id, user_id, rating, reason, created_at, applied_preference_id)`
`preferences(preference_id, user_id, task_id NULL, scope, kind, value_json, created_from_feedback_id, created_at, revoked_at)`
偏好作用域严格 `include\|exclude\|frequency_cap`,且 task_id 限定作用范围(F10/N7);撤销(soft revoke)仅影响未来执行。

### Identity

`users(user_id, display_name, timezone, created_at)`
`channel_identities(channel_key, channel_user_id, user_id, status, confirmed_at, confirm_token, confirm_expires_at)`
status: `pending\|bound\|unbinding`;绑定需 token + 主渠道二次确认(F1)。
`identity_events` 追加写记录绑定/解绑发起与确认(N14)。

入站解析区分 `unknown`、`pending`、`bound`、`unbinding`：`unknown` 通过首次渠道注册创建独立 user 后继续原消息；`pending/unbinding` 返回绑定状态提示且不读取旧数据；只有 `bound` 注入既有 user_id。首次注册不是跨渠道合并，不需要二次确认。

## 模块设计

### storage (基础设施)

**职责:** 单 SQLite 文件管理,迁移、连接池、按 user_id 强制查询隔离。
**对外接口:**
- `storage.open(path) -> Store`
- `Store.transaction(...)` 返回上下文管理器
- 仓储对象 `Repo.for_user(user_id)` 返回所有查询都强制 `WHERE user_id=?` 的 facade(N1)
- `Store.migrate(target_version)` 启动幂等迁移
**依赖:** stdlib sqlite3+WAL;anyio.to_thread 包裹阻塞调用(避免阻塞事件循环)
**约束:** 任何业务层禁止直接使用 sqlite3 连接;必须经 `Repo.for_user`

### identity (F1)

**职责:** 解析渠道入站身份为 canonical user_id;绑定/解绑的发起、token、二次确认、过期、状态审计。
**对外接口:**
- `IdentityRegistry.resolve(channel_key, channel_user_id) -> ResolveResult(user_id|None, needs_binding)`
- `IdentityRegistry.start_binding(initiator_user_id, target_channel_key, target_channel_user_id, ttl) -> token`
- `IdentityRegistry.confirm_binding(token, via_channel_key) -> bound_user_id|Error`
- `IdentityRegistry.start_unbind(user_id, channel_key, channel_user_id) -> UnbindImpact`(预先向用户展示数据归属)
- `IdentityRegistry.confirm_unbind(token, via_channel_key) -> Result`
**依赖:** storage;`channels/`(仅读取 channel_user_id 概念,不调用业务)
**集成点:** `channels/*/plugin.py` 的入站处理在路由前先调用 `IdentityRegistry.resolve`,拿到 user_id 后才进入 mvp 业务路径。channels 不感知任务语义(4.3 核心约束)。
**审计:** 所有绑定/解绑写入 `identity_events`,按 N1 不返回明文凭据。

### scheduler (F2 F4 F13)

**职责:** WatchTask CRUD/版本化、规范化、模板校验、计划生成、到期分发、并发与重叠控制、手动触发、暂停/恢复/逻辑删除收敛。
**对外接口:**
- `TaskService.create(user_id, draft) -> TaskCreateResult{(task_id, normalized_summary, ok|missing_fields[])}`
- `TaskService.confirm(user_id, task_id, normalized_version_id) -> task`(启用前必须 confirm,F2)
- `TaskService.update/pause/resume/delete(user_id, task_id, ...) -> task`(变更写新 version 行)
- `TaskService.trigger_now(user_id, task_id) -> execution_id`(手动触发不破坏周期)
- `SchedulerLoop.tick(now)` 由 boot 启动的 anyio task 每 30s 调用,内部:
  1. 扫 `WHERE status='pending' AND scheduled_at<=now` 且 task status='active'
  2. CAS 转 running、写 started_at/heartbeat_at
  3. 委派给 `Collector` 执行(避免同 task 重叠:同一 task_id 已有 running 时跳过并记 skipped)
- `SchedulerLoop.recover(now)` 启动时调用:扫 `status='running' AND heartbeat_at < now - HEARTBEAT_TIMEOUT`,收敛为 `recovered` 并记原状态(F12、AC18)
**频率:** 自定义 `frequency_seconds` 必须在 900~604800(15min..7day),越界拒绝(不静默截断,F4)。
**限额:** `max_tasks_per_user`、`max_concurrent_executions_global` 从 config 读,达上限返回受限错误(非排队,F4);值由 observing 暴露(N8)。
**依赖:** storage、identity

### collector (F3 F5 N9 N11 N12)

**职责:** 给定 pending Execution,展开来源列表(URL+搜索关键词),逐源访问、robots 检查、限速、错误分类、快照写作;不跨源判断。
**对外接口:**
- `Collector.run(execution_id) -> ExecutionResult`(异步,内部按域名并发=1、间隔≥2s)
- `Collector.heartbeat(execution_id)`(供 scheduler 重启侦测)
**子组件:**
- `SourceExpander` 从 source_scope 生成 `SourcePlan[]`(关键词走 SearchProvider,URL 直接成计划项)
- `RobotsCache` 缓存 robots.txt + 显式 ToS 表;被禁路径直接置 blocked(N11、AC3)
- `FetchClient` 抽象,默认 httpx 实现;尊重 Retry-After、429 退避(N11、N12);沙盒策略调用 `tools/sandbox/policy` 拒绝本机/内网/云元数据(N1)
- `SnapshotWriter` 用 `content_hash` 判 `unchanged`(不重复写快照,F5);changed 写新 snapshot 并链接 previous
- `ErrorClassifier` 按 N12 表分类,只写不重试或按上限重试
**约束:** 单源失败不阻断其他源(F12);错误页/登录页/验证码页由 `ContentGuard` 判定后置 blocked 不写有效变化(F5、AC5)
**依赖:** storage、identity、tools/sandbox/policy(只读)、extensions 的 `SearchProvider`/`ModelProvider` 接口

### analyzer (F6 F7 F8 N6 N7)

**职责:** 基于 Snapshot 做变化检测、跨源去重、价值判断、信号合成、决策简报生成;唯一可写 Signal.status 和 Brief.sendable 的层(4.3)。
**对外接口:**
- `Analyzer.run(execution_id) -> AnalysisResult` 输入快照,产出 proposed/suppressed 信号和 sendable 简报
- `Analyzer.judge(change, task_version, preferences) -> Verdict`(相关性/重要性/新颖性/来源可信度/不确定性)
**子组件:**
- `ChangeDetector` diff normalized content,过滤广告/时间戳/布局噪声(F6)
- `CrossSourceDeduper` 跨源合并,保守阈值;记录合并依据(实体/标题相似度/时间窗),保留各原始来源入口(F6、AC6)
- `DedupWindow` 72h 内同 task + dedup_key 命中已 notified → `deduped`(F9、AC7)
- `PreferenceFilter` 应用 feedback 层提供的显式偏好,作用域严格不超出当前 task(F10、AC17);未提供偏好时保守过滤(F7)
- `BriefBuilder` 调用 `ModelProvider`(走 extensions 接口,N6)产出 facts/inferences/next_steps/source_refs;缺失 source_refs 或 captured_at 时 `sendable=false`(AC8);高 uncertainty 不进入即时通知(N4、F8)。
**模型降级:** provider 不可用时按 N6 真实降级,简报置 sendable=false 并在 brief 标记 failure_summary(不伪造)
**依赖:** storage、identity、extensions、feedback(只读偏好)

### notifier (F9 F13)

**职责:** 消费 sendable brief,选渠道、免打扰延迟、跨渠道去重、额度控制、发送、有限重试、最终状态落库。
**对外接口:**
- `Notifier.enqueue(brief_id, signal_ids) -> DeliveryPlan`
- `Notifier.drain_due(now)` 由 scheduler loop tick 调用,处理 deferred 到期发送
**子组件:**
- `DoNotDisturbCalculator` 按 user 时区(N10)推断延迟目标时间,跨零点/夏令时边界仍正确(N10、AC16)
- `DedupGate` 同 signal 同 channel 唯一,跨渠道总量≤已绑定渠道数(F9、AC9);超额置 suppressed
- `ChannelAdapter` 抽象 web/feishu 出站,新增渠道不复制业务逻辑(N5)
- `RetryPolicy` 按 N12 表针对不同 delivery 错误码退避;不可恢复错误停止重试
**约束:** notifier 不重新改变 Signal.status(4.3)
**依赖:** storage、identity、channels(只写出站)、observing(只写事件)

### feedback (F10 F13)

**职责:** 接收 rating/useless/too_frequent + reason、映射为显式偏好并落库、提供可见可枚举可撤销的偏好视图、导出。
**对外接口:**
- `FeedbackService.submit(user_id, delivery_id, rating, reason) -> feedback_id`
- `PreferenceService.list_for_task(user_id, task_id) -> PreferenceView[]`(包含 `applies_to`、`originating_feedback_id`)
- `PreferenceService.revoke(user_id, preference_id)` soft revoke,不回改已交付简报(N14)
- `PreferenceService.apply_filter(task_id, change) -> include|exclude|score_adjust`(供 analyzer 调用)
**约束:** 单次负面不永久屏蔽整主题/整来源(F10);不存在跨用户写入路径(AC17)
**依赖:** storage、identity

### observing (F11 N4 N8)

**职责:** 结构化事件总线、指标计数、追溯链路、敏感字段脱敏。
**对外接口:**
- `Observing.emit(event)` 必带 `execution_id/task_id/user_id` 关联键(N4)
- `Metrics` 计数器:`task_run_success_rate/source_fail_rate/signal_yield_rate/delivery_success_rate/duplicate_delivery_rate/feedback_count`(F11、N8)
- `Trace` 提供从 delivery → brief → signal → change → source 的追溯查询接口(F11、AC11)
- `Redactor` 脱敏凭据/敏感内容,基于 N1 与 config.redact_sensitive 规则
**依赖:** storage(只写 `events` 表)

## 模块交互

### 典型执行链路(spec 6.1 / AC14 端到端)

```
cron tick
  → SchedulerLoop.tick
    → 收集 pending executions, CAS running
    → Collector.run(execution_id)
        SourceExpander → RobotsCache → FetchClient(+sandbox) → SnapshotWriter
       产出 SourceHit + Snapshot
    → Analyzer.run(execution_id)
        ChangeDetector → CrossSourceDeduper → PreferenceFilter(feedback 读) → BriefBuilder(model)
       产出 Signal(proposed/suppressed) + Brief(sendable?)
    → Analyze 完成后将 Execution.status 写 partial/succeeded/failed
  → Notifier.drain_due / enqueue
    DoNotDisturbCalculator → DedupGate → ChannelAdapter → RetryPolicy
    产 Delivery(delivered/retry/failed/deferred/suppressed)
  → Observing.emit 各阶段事件
```

### 用户创建任务链路(F2 / AC2)

```
入站消息(channels) → IdentityRegistry.resolve → 若无 binding 走 binding 流程
  → TaskService.create(draft) 返回 normalized_summary + missing_fields[]
  → 若 missing 非空,2 轮内补充,否则切换表单或终止(F2)
  → TaskService.confirm → 生成首个 pending Execution(按 frequency)
  → channels 出站回规范化摘要
```

### 反馈链路(F10 / AC10)

```
入站 rating → IdentityRegistry.resolve → FeedbackService.submit
  → PreferenceService 合成 preference(可枚举、可见) → analyzer 后续 run 读取
  → PreferenceService.revoke 可撤销,影响未来执行
```

### 重启恢复(F12 / AC4)

```
boot 启动:
  SchedulerLoop.recover(now)
    扫 running + heartbeat_at < now - HEARTBEAT_TIMEOUT
    当原状态不明 → 写 status='recovered',status_history 记录原 running(AC18)
  继续后续 tick
```

## 文件组织

```
backend/src/watchlight/
├── storage/
│   ├── __init__.py
│   ├── store.py            # Store、Repo.for_user、连接池、WAL
│   ├── migrations.py        # schema_version + 顺序迁移函数
│   ├── repos/
│   │   ├── tasks.py
│   │   ├── executions.py
│   │   ├── snapshots.py
│   │   ├── signals.py
│   │   ├── briefs.py
│   │   ├── deliveries.py
│   │   ├── feedback.py
│   │   └── events.py
│   └── blobs.py             # snapshot blob 落盘
├── identity/
│   ├── __init__.py
│   ├── registry.py          # IdentityRegistry
│   ├── binding.py           # start/confirm binding、unbinding impact
│   └── audit.py             # identity_events 追加写
├── scheduler/
│   ├── __init__.py
│   ├── service.py           # TaskService CRUD + 规范化 + 模板
│   ├── normalize.py         # 自然语言 draft → normalized 摘要 + missing
│   ├── templates.py         # 6.1/6.2/6.3 三套模板
│   ├── loop.py              # SchedulerLoop.tick/recover + 重叠控制
│   └── limits.py            # max_tasks/max_concurrency config 读取
├── collector/
│   ├── __init__.py
│   ├── runner.py            # Collector.run
│   ├── expander.py          # SourceExpander + Search Provider 注入
│   ├── robots.py            # RobotsCache
│   ├── fetch.py             # FetchClient 抽象 + httpx 默认实现
│   ├── content_guard.py     # 登录/验证码/付费墙/错误页判定
│   ├── snapshot.py          # SnapshotWriter + content_hash
│   └── errors.py            # ErrorClassifier 按 N12 表
├── analyzer/
│   ├── __init__.py
│   ├── runner.py            # Analyzer.run
│   ├── change.py            # ChangeDetector
│   ├── dedupe.py            # CrossSourceDeduper + DedupWindow
│   ├── value.py             # PreferenceFilter + Verdict
│   ├── brief.py             # BriefBuilder + Model Provider 注入
│   └── degrade.py           # 模型不可用真实降级(N6)
├── notifier/
│   ├── __init__.py
│   ├── queue.py             # enqueue + drain_due + RetryPolicy
│   ├── dnd.py               # DoNotDisturbCalculator
│   ├── dedup.py             # DedupGate
│   └── channels.py          # ChannelAdapter 注册 web/feishu 出站
├── feedback/
│   ├── __init__.py
│   ├── service.py           # FeedbackService.submit
│   ├── preferences.py       # PreferenceService list/revoke/apply_filter
│   └── export.py            # 数据导出(F13)
├── observing/
│   ├── __init__.py
│   ├── events.py            # emit + event 表
│   ├── metrics.py           # 计数器
│   ├── trace.py             # 追溯查询(delivery→brief→signal→change→source)
│   └── redact.py            # Redactor
└── gateway/                  # 现有目录追加方法模块
    ├── methods/
    │   ├── watch_tasks.py     # REST: 任务 CRUD/confirm/pause/trigger
    │   ├── watch_exec.py      # 历史/执行详情
    │   ├── watch_signals.py   # 信号、简报、追溯
    │   ├── watch_delivery.py  # 通知、反馈提交
    │   └── watch_identity.py  # 绑定发起/确认/解绑
    └── boot_watchshed.py      # 在 boot 中:open Store、migrate、start SchedulerLoop/Notifier drain
```

## 技术决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 持久化 | 单文件 SQLite + WAL | spec/用户决策;AC4 重启恢复、AC12 收敛、N2 幂等可由 SQL 事务保证;与单进程部署一致;后续可迁移 PG |
| 调度 | 进程内 anyio loop,30s tick + CAS | spec/用户决策;N2 5min 内执行→30s tick 足够余量;CAS 避免多实例前提下的重复(AC4) |
| 同任务不重叠 | scheduler 维护 `task_id→running` 内存表 + DB CAS 双重 | F4 不无边界重叠;recovery 后该表重建自 DB |
| 心跳收敛 | heartbeat_at + HEARTBEAT_TIMEOUT(默认 10min) | F12/AC18;从 running → recovered 必须明确显式 |
| ID | UUIDv7 时间有序 | 便于按时间切片、追加写(N14) |
| 时间存储 | UTC POSIX 秒 (int) | N10 明确要求;调度比较统一 UTC;展示按 user 时区渲染 |
| ORM | 无 ORM,stdlib sqlite3 + pydantic 模型 + Repo facade | 与现有项目无 ORM 一致;依赖最小;Repo.for_user 强制隔离(N1) |
| 异步 DB | anyio.to_thread 包裹 | sqlite 同步 API;避免阻塞事件循环 |
| 模型/搜索抽象 | 复用 extensions 的 Provider 接口,但 analyzer/collector 不直接 import 具体名 | N6 可替换;analyzer 仅依赖 `ModelProvider` 契约 |
| 网络沙盒 | collector 复用 tools/sandbox/policy 拒绝本机/内网/元数据 | N1;避免在采集层重写安全策略 |
| 渠道解耦 | identity/notifier 调用 channels 的接口,业务层零飞书/Web 专有概念 | 4.3 核心约束、N5 |
| Robots | RobotsCache + 显式 ToS 表 | N11/AC3;被禁路径置 blocked 不绕过 |
| 错误分类 | 表驱动,N12 五类一一对应 classifier | 不可任意层自发明重试规则 |
| 去重键 | analyzer 计算并持久化 dedup_key,notifier 仅消费 | F9 强制;防止跨层不一致 |
| 偏好范围 | preferences.task_id 必填(或 user-global 显式标记);撤销 soft revoke | AC17;不存在跨用户写入 |
| 反向验收 | TaskService/Analyze 显式拒绝清单匹配 N10 不做事项 | AC15;拒绝时返回 `unsupported_action` 而非误导性"已受理" |
| 配置 | 复用 config/ + 新增 `watchshed` section 在 WatchlightConfig | 与现有 config 一致;observing 暴露限额(N8) |
| 测试样本 | fixtures/ 下提供固定来源样本 + 确定性时间 | N8/AC14 可重复验证完整链路 |

## 需求覆盖矩阵(spec.md → 本 plan 归属模块)

| spec | 归属模块 |
|------|----------|
| F1 | identity |
| F2 | scheduler.service + normalize + templates |
| F3 | collector.expander + content_guard |
| F4 | scheduler.loop + limits + recover(F12 交叉) |
| F5 | collector.snapshot + content_guard |
| F6 | analyzer.change + dedupe |
| F7 | analyzer.value + analyzer.dedupe(DedupWindow) |
| F8 | analyzer.brief + degrade |
| F9 | notifier.queue + dnd + dedup + channels |
| F10 | feedback.service + preferences |
| F11 | observing.events + trace + gateway.methods.watch_exec |
| F12 | scheduler.recover + collector.errors + notifier.retry |
| F13 | feedback.export + scheduler.service.delete + notifier.draining |
| N1 | storage.Repo.for_user + collector.content_guard + sandbox/policy + observing.redact |
| N2 | scheduler.CAS + recover + Notifier.idempotent enqueue(基于 dedup_key) |
| N3 | collector 单源超时 + scheduler 并发上限 |
| N4 | observing.redact + analyzer 不暴露提示词 |
| N5 | notifier ChannelAdapter + identity 不感知业务 |
| N6 | adapter 走 extensions Provider 抽象 + analyzer.degrade |
| N7 | feedback.preferences 仅显式偏好 + scope 限定 |
| N8 | observing.metrics + fixtures |
| N9 | collector.robots + content_guard |
| N10 | storage UTC int + Notifier.dnd 按 user 时区 + 展示层渲染 |
| N11 | collector.robots + fetch 限速(域名并发1、间隔2s) |
| N12 | collector.errors + notifier.retry 表驱动 |
| N13 | extensions Provider 接口抽象(已有) |
| N14 | storage 追加写表 + task_versions + soft revoke |
| AC1~AC19 | 与 F/N 对应模块;checklist.md 细化 |

完成:每条 F/N 都有归属模块,无缺口。

## 已批准补充：回复渲染设计

自然语言任务流程先把 normalized summary 交给人类可读格式化函数，再输出 Markdown 文本；不得直接插值内部 dict。Web 保留 Markdown 文本供前端渲染，飞书 ChannelAdapter 将 Markdown 包装为 interactive card 的 markdown element；若飞书拒绝卡片消息，再回退到现有 text 消息。

Web 使用无 `v-html` 的结构化 Markdown 解析器，将标题、段落、强调、列表、引用、链接、行内代码和代码块解析为 Vue 节点；链接只允许 `http/https`，原始 HTML 始终作为文本显示。模型流式输出和最终通道回复复用同一组件。
