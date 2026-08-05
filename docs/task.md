# Watchlight MVP Tasks

> 输入：`docs/spec.md` v0.4 + `docs/plan.md`
> 依赖方向严格遵循 plan 架构图,task ID 严格按可执行顺序;依赖前置未完成不得开做。
> 约定:
> - 验证命令默认在仓库根 `D:\watchlight` 执行
> - `ruff check`、`mypy backend/src` 是每个任务结束的基线检查(下文简称「lint」)
> - 单元测试与被测代码同结构放在 `tests/watchlight/...`
> - 每个任务运行验证后必须看到实际输出再标记完成

## 文件清单

| 操作 | 文件 | 职责 |
|------|------|------|
| 新建 | `backend/src/watchlight/storage/__init__.py` | storage 包入口 |
| 新建 | `backend/src/watchlight/storage/store.py` | Store/Repo.for_user/连接/WAL |
| 新建 | `backend/src/watchlight/storage/migrations.py` | schema_version + 顺序迁移函数 |
| 新建 | `backend/src/watchlight/storage/blobs.py` | snapshot blob 落盘读写 |
| 新建 | `backend/src/watchlight/storage/repos/__init__.py` | repos 包入口 |
| 新建 | `backend/src/watchlight/storage/repos/tasks.py` | WatchTask + version 仓储 |
| 新建 | `backend/src/watchlight/storage/repos/executions.py` | Execution 仓储 |
| 新建 | `backend/src/watchlight/storage/repos/snapshots.py` | Snapshot + Change 仓储 |
| 新建 | `backend/src/watchlight/storage/repos/signals.py` | Signal 仓储 |
| 新建 | `backend/src/watchlight/storage/repos/briefs.py` | Brief 仓储 |
| 新建 | `backend/src/watchlight/storage/repos/deliveries.py` | Delivery 仓储 |
| 新建 | `backend/src/watchlight/storage/repos/feedback.py` | Feedback + Preference 仓储 |
| 新建 | `backend/src/watchlight/storage/repos/events.py` | observing 事件 仓储 |
| 新建 | `backend/src/watchlight/storage/repos/identity.py` | users + channel_identities + identity_events |
| 新建 | `backend/src/watchlight/identity/__init__.py` | identity 包入口 |
| 新建 | `backend/src/watchlight/identity/registry.py` | IdentityRegistry.resolve/start/confirm |
| 新建 | `backend/src/watchlight/identity/binding.py` | binding token + unbinding impact |
| 新建 | `backend/src/watchlight/identity/audit.py` | identity_events 追加写 |
| 新建 | `backend/src/watchlight/scheduler/__init__.py` | scheduler 包入口 |
| 新建 | `backend/src/watchlight/scheduler/normalize.py` | draft → normalized + missing_fields |
| 新建 | `backend/src/watchlight/scheduler/templates.py` | 6.1/6.2/6.3 三套模板 |
| 新建 | `backend/src/watchlight/scheduler/service.py` | TaskService CRUD + 版本化 + confirm |
| 新建 | `backend/src/watchlight/scheduler/limits.py` | max_tasks/max_concurrency 读取 |
| 新建 | `backend/src/watchlight/scheduler/loop.py` | SchedulerLoop.tick/recover + 重叠控制 |
| 新建 | `backend/src/watchlight/collector/__init__.py` | collector 包入口 |
| 新建 | `backend/src/watchlight/collector/expander.py` | SourceExpander + SearchProvider 接口 |
| 新建 | `backend/src/watchlight/collector/robots.py` | RobotsCache + ToS 表 |
| 新建 | `backend/src/watchlight/collector/fetch.py` | FetchClient 抽象 + httpx 默认实现 |
| 新建 | `backend/src/watchlight/collector/content_guard.py` | 登录/验证码/付费墙/错误页判定 |
| 新建 | `backend/src/watchlight/collector/snapshot.py` | SnapshotWriter + content_hash |
| 新建 | `backend/src/watchlight/collector/errors.py` | ErrorClassifier 按 N12 表 |
| 新建 | `backend/src/watchlight/collector/runner.py` | Collector.run 编排 |
| 新建 | `backend/src/watchlight/analyzer/__init__.py` | analyzer 包入口 |
| 新建 | `backend/src/watchlight/analyzer/change.py` | ChangeDetector |
| 新建 | `backend/src/watchlight/analyzer/dedupe.py` | CrossSourceDeduper + DedupWindow |
| 新建 | `backend/src/watchlight/analyzer/value.py` | PreferenceFilter + Verdict |
| 新建 | `backend/src/watchlight/analyzer/brief.py` | BriefBuilder + ModelProvider 接口 |
| 新建 | `backend/src/watchlight/analyzer/degrade.py` | 模型不可用真实降级 |
| 新建 | `backend/src/watchlight/analyzer/runner.py` | Analyzer.run 编排 |
| 新建 | `backend/src/watchlight/notifier/__init__.py` | notifier 包入口 |
| 新建 | `backend/src/watchlight/notifier/dnd.py` | DoNotDisturbCalculator |
| 新建 | `backend/src/watchlight/notifier/dedup.py` | DedupGate |
| 新建 | `backend/src/watchlight/notifier/channels.py` | ChannelAdapter 注册 web/feishu 出站 |
| 新建 | `backend/src/watchlight/notifier/queue.py` | enqueue + drain_due + RetryPolicy |
| 新建 | `backend/src/watchlight/feedback/__init__.py` | feedback 包入口 |
| 新建 | `backend/src/watchlight/feedback/service.py` | FeedbackService.submit |
| 新建 | `backend/src/watchlight/feedback/preferences.py` | PreferenceService list/revoke/apply_filter |
| 新建 | `backend/src/watchlight/feedback/export.py` | 数据导出 |
| 新建 | `backend/src/watchlight/observing/__init__.py` | observing 包入口 |
| 新建 | `backend/src/watchlight/observing/events.py` | emit + event 表 |
| 新建 | `backend/src/watchlight/observing/metrics.py` | 计数器 |
| 新建 | `backend/src/watchlight/observing/trace.py` | 追溯查询 delivery→brief→signal→change→source |
| 新建 | `backend/src/watchlight/observing/redact.py` | Redactor |
| 修改 | `backend/src/watchlight/contracts/config/types_watchlight.py` | 新增 `watchshed` section 字段 |
| 修改 | `backend/src/watchlight/gateway/boot.py` | 注入 boot_watchshed:open Store/migrate/start loops |
| 新建 | `backend/src/watchlight/gateway/boot_watchshed.py` | 新子模块,被 boot.py 调用 |
| 新建 | `backend/src/watchlight/gateway/methods/watch_tasks.py` | REST: 任务 CRUD/confirm/pause/trigger |
| 新建 | `backend/src/watchlight/gateway/methods/watch_exec.py` | 历史/执行详情 |
| 新建 | `backend/src/watchlight/gateway/methods/watch_signals.py` | 信号、简报、追溯 |
| 新建 | `backend/src/watchlight/gateway/methods/watch_delivery.py` | 通知、反馈提交 |
| 新建 | `backend/src/watchlight/gateway/methods/watch_identity.py` | 绑定发起/确认/解绑 |
| 修改 | `backend/src/watchlight/gateway/app.py` | 注册 watch_* 路由 |
| 修改 | `backend/src/watchlight/channels/*/plugin.py`(feishu/webchat) | 入站前调用 IdentityRegistry.resolve |
| 新建 | `tests/watchlight/conftest.py` | 共享 store fixture + 时间冻结 |
| 新建 | `tests/watchlight/test_storage_*.py` | 每个子模块对应测试 |
| 新建 | `tests/watchlight/test_identity.py` | 绑定/解绑/二次确认/过期 |
| 新建 | `tests/watchlight/test_scheduler_*.py` | CRUD/版本/频率边界/重叠/恢复 |
| 新建 | `tests/watchlight/test_collector_*.py` | 状态分类/快照去重/robots/限速 |
| 新建 | `tests/watchlight/test_analyzer_*.py` | 变化/去重/价值/简报 sendable/降级 |
| 新建 | `tests/watchlight/test_notifier_*.py` | dnd/跨渠道去重/重试/额度 |
| 新建 | `tests/watchlight/test_feedback.py` | 反馈偏好/作用域/撤销 |
| 新建 | `tests/watchlight/test_observing.py` | 追溯链路/脱敏 |
| 新建 | `tests/watchlight/test_e2e.py` | AC14 端到端固定样本完整链路 |
| 新建 | `fixtures/watchlight/sources/` | 固定来源样本(HTML) + manifest |
| 新建 | `fixtures/watchlight/expected/` | 预期快照 hash、变化、简报期望 |

---

## T1: storage 基础设施

**文件:** `backend/src/watchlight/storage/store.py`、`__init__.py`
**依赖:** 无
**步骤:**
1. 定义 `Store` 类,持有 sqlite3 连接(WAL 模式)、connect 路径、`schema_version` 表
2. 实现 `Store.open(path) -> Store` 类方法:打开连接、PRAGMA `journal_mode=WAL; foreign_keys=ON; synchronous=NORMAL`
3. 实现 `Store.transaction()` async context,内部用 anyio.to_thread.run_sync 包裹 `BEGIN...COMMIT/ROLLBACK`
4. 实现 `Repo.for_user(store, user_id) -> Repo` facade:所有仓储方法在 SQL 末尾强制 `AND user_id=?`,而非 SQL 模板拼凑(用参数绑定)
5. 暴露 `Store.close()`
**验证:** `python -c "from watchlight.storage import Store; s=Store.open(':memory:'); s.close(); print('ok')"` 输出 ok;lint 过

## T2: 存储 schema 迁移

**文件:** `backend/src/watchlight/storage/migrations.py`
**依赖:** T1
**步骤:**
1. 定义 `MIGRATIONS: list[tuple[int, str]]`(version→SQL)
2. 第一个迁移建 `schema_version` 表 + 11 张业务表(plan 核心数据结构节):`users`、`channel_identities`、`identity_events`、`watch_tasks`、`watch_task_versions`、`executions`、`source_hits`、`snapshots`、`snapshot_blobs`、`changes`、`signals`、`briefs`、`deliveries`、`feedbacks`、`preferences`、`events`
3. 状态字段用 `TEXT CHECK IN (...)` 约束对应 spec 4.1 枚举
4. `task_version_id` / `previous_snapshot_id` 等外键,但默认 sqlite PRAGMA `foreign_keys=ON`
5. 实现 `migrate(store)` 函数:读 `schema_version`,逐个应用未应用迁移并更新版本号;再调用幂等(已应用版本跳过)
**验证:** `python -m pytest tests/watchlight/test_storage_migrations.py -q` 通过(此测试先随 T2 一并写);新 db.migrate 后再 migrate 不重复建表;`SELECT name FROM sqlite_master WHERE type='table'` 必须含全部 16 张表名;lint 过

## T3: 仓储基类与隔离

**文件:** `backend/src/watchlight/storage/repos/__init__.py`、`backend/src/watchlight/storage/repos/tasks.py`(只放 tasks 占位,留 T5 实现)、同样的 `executions.py` 等占位
**依赖:** T2
**步骤:**
1. 在 `repos/__init__.py` 定义 `Repo` dataclass:持有 `store` 与 `user_id`,提供 `execute(sql, params)` 强制注入 `user_id` 占位参数
2. 实现一个 `_assert_user_filter(select_sql)` 帮助函数:校验 SQL 中至少有一个不允许绕过 user_id 过滤的方法或硬注入 `AND user_id = :uid`
3. 写测试 `tests/watchlight/test_storage_repo_isolation.py`:两个不同 user_id 写入各自 task,互相 SELECT 互不见
**验证:** `pytest tests/watchlight/test_storage_repo_isolation.py -q` 绿;lint 过

## T4: snapshot blob 落盘

**文件:** `backend/src/watchlight/storage/blobs.py`
**依赖:** T2
**步骤:**
1. 定义 `BlobStore(blob_root: Path)`:`put(blob_id, kind, bytes) -> ref`、`get(ref) -> bytes`
2. blob 文件以 `blob_id` 前 2 位做分桶目录,避免单目录过多文件
3. 在 `Store` 中维护 `snapshot_blobs` 表(`blob_id PK, kind, created_at`),ref 字符串规则为 `<blob_id>.<kind>`
4. 写测试验证写入可读回、同 blob_id 重复 put 不覆盖(N14 追加写)
**验证:** `pytest tests/watchlight/test_storage_blobs.py -q` 绿;lint 过

## T5: WatchTask 仓储(含版本化)

**文件:** `backend/src/watchlight/storage/repos/tasks.py`
**依赖:** T3
**步骤:**
1. 实现 `create(user_id, draft_fields) -> WatchTask`:写入 `watch_tasks` 同时插入第 1 行 `watch_task_versions(version=1, snapshot_json=...)`,设置 `current_version_id`
2. 实现 `get(user_id, task_id)`、`list(user_id, status=None)` 都强制 user_id 过滤
3. 实现 `update(user_id, task_id, changes) -> WatchTask`:写新 `watch_task_versions(version+1)` 行,更新主表 `current_version_id`、`updated_at`、`version`(N14、F2)
4. 实现 `set_status(user_id, task_id, status)`:状态变更 `active|paused|draining|deleted`,且 `draining→deleted` 是审计期后才允许(此处仅提供 API,实际收敛由 T8 loop 控制)
5. 实现 `version_history(user_id, task_id)` 返回按 version 顺序
6. 写测试:创建→修改→版本列表应为 2 条且 version 单调;deleted 状态不出现在普通 `list()`(N14)
**验证:** `pytest tests/watchlight/test_storage_repos_tasks.py -q` 绿;lint 过

## T6: Execution / SourceHit / Snapshot / Change / Signal / Brief / Delivery / Feedback / Preference / Event 仓储

**文件:** `backend/src/watchlight/storage/repos/{executions,snapshots,signals,briefs,deliveries,feedback,events}.py`
**依赖:** T3
**步骤:**
1. 每张表一个 repo,只暴露 `insert/get/list_for_task/update_status`(对应状态枚举严格用 plan 定义名)
2. `executions`:`list_pending_locked(now)` 用于 scheduler tick,`heartbeat(execution_id, now)`,`recover_candidates(now, timeout)` 用于 T8
3. `signals`:`status_history_json` 追加写流转记录(AC18)
4. `deliveries`:`find_due(now)` 用于 notifier drain
5. `events`:`insert(event)`(`event` dict 必含 `execution_id/task_id/user_id`),`list_by_execution(execution_id)`
6. 写测试覆盖每个 repo 状态枚举 CHECK 约束生效、追加写不覆盖
**验证:** `pytest tests/watchlight/test_storage_repos_*.py -q` 绿;lint 过

## T7: Identity 仓储

**文件:** `backend/src/watchlight/storage/repos/identity.py`
**依赖:** T3
**步骤:**
1. `create_user(display_name, timezone) -> user_id`,默认 timezone 由 N10 推断
2. `find_channel_identity(channel_key, channel_user_id)`、`bind(initiator_user_id, target_channel_key, target_channel_user_id, ttl) -> token`(写入 channel_identities status=pending + identity_events)
3. `confirm_binding(token, via_channel_key) -> bound_user_id|Error`:校验过期、状态置 bound、user_id 合并(若 channel 原已有独立 user 在绑定时归并入主 user_id,但 spec F1 要求"未完成绑定的两个渠道身份不得自动合并",所以 pending 期不得有读写串数据 → 这里仅维护绑定关系,真正合并由 T9 在 resolve 层判断绑定完成后再透明切换)
4. `unbind(user_id, channel_key, channel_user_id) -> UnbindImpact`:预先查询该渠道绑定的哪些任务会产生归属迁移(F1)
5. `start_unbind` / `confirm_unbind` 双阶段
6. 写测试覆盖过期、二次确认、未确认不得串数据
**验证:** `pytest tests/watchlight/test_storage_repos_identity.py -q` 绿;lint 过

## T8: IdentityRegistry(F1 核心)

**文件:** `backend/src/watchlight/identity/registry.py`、`binding.py`、`audit.py`、`__init__.py`
**依赖:** T7
**步骤:**
1. `resolve(channel_key, channel_user_id) -> ResolveResult`:命中 bound 直接返回 user_id;未命中返回 `needs_binding=True` 且**不返回任何其他用户数据**(AC1)
2. `start_binding(initiator_user_id, target_channel_key, target_channel_user_id) -> token`:TTL 从 config 读(默认 30min,F1 要求有失效),写入 channel_identities.status=pending 与 identity_events 事件
3. `confirm_binding(token, via_channel_key)`:必须是死锁的二次确认,不允许多渠道同时确认同 token;成功后所有后续 resolve 命中 bound;合并场景下原任务/历史/反馈归属不变,只是后续渠道身份的 user_id 路由到当前主 user_id
4. `start_unbind(user_id, channel_key)`:必须先返回 UnbindImpact 向用户展示数据归属(F1 的硬性要求)
5. `confirm_unbind(token, via_channel_key)`:成功后 channel_identity.status=unbinding 并立即失效 resolve(不再读到原用户数据)
6. `audit.append` 在每个 binding/unbinding 节点写 identity_events
7. 写测试 T9 风格:resolve 在未绑定/绑定中/过期 各自行为;绑定未确认前两渠道互不可见对方任务(AC1)
**验证:** `pytest tests/watchlight/test_identity.py -q` 绿;lint 过

## T9: 把 identity 接入 channels 入站

**文件:** `backend/src/watchlight/channels/feishu/plugin.py`、`webchat/plugin.py`(修改)
**依赖:** T8
**步骤:**
1. 在各 plugin 入站路径,首步先调用 `IdentityRegistry.resolve(channel_key, channel_user_id)`
2. 从未出现过的 `unknown` 身份:调用首次渠道注册创建独立 user,把 user_id 注入上下文并继续原消息,不得阻断原有普通对话
3. `pending/unbinding`:返回绑定状态提示(不暴露内部其它用户),且不得自动创建同名新账号
4. 已绑定:把 user_id 注入到本次会话上下文,mvp 业务调用统一从 user_id 出发
5. 不修改 channels 包对外契约(N5),channels 仍不感知任务语义
**验证:** `pytest tests/watchlight/test_channels_identity.py -q` 绿;覆盖首次飞书消息自动注册、pending 拦截、解绑后不自动重建;lint 过

## T10: TaskService CRUD + 规范化 + 模板

**文件:** `backend/src/watchlight/scheduler/service.py`、`normalize.py`、`templates.py`、`limits.py`
**依赖:** T5
**步骤:**
1. `templates.py`:三个模板字面量(技术动态追踪 / 指定页面变化 / 求职信息追踪),各自含 `target/source_scope/trigger_condition/frequency/notification_policy` 占位(F2)
2. `normalize.py`:`normalize(draft) -> NormalizedResult{summary, missing_fields[]}`;缺失频率或通知策略时返回 missing 且**不采用默认值**(F2 不允许静默默认)
3. `service.create(user_id, draft, via='nl'|'form') -> CreateResult`:返回 normalized_summary + missing_fields;`missing` 非空时不写库,等待补全
4. `service.confirm(user_id, task_id, normalized_version_id)`:必须由用户确认规范化摘要后才置 status=active 并生成首个 pending Execution(F2)
5. `service.update/pause/resume`:update 走 T5 的版本化写新行;pause 改 status=paused(不生成新计划)
6. `service.delete`:置 draining;不立即 deleted
7. `limits.check_task(user_id) -> LimitResult`:超过 max_tasks 返回拒绝(非排队,F4)
8. `limits.check_concurrency_global()` 同上;值从 config 读(由 T22 注入)
9. 写测试:`missing` 时 create 不落库;confirm 后 task.status=active 且有对应 pending execution;update 后 version 自增;频率 900..604800 边界拒绝;超额返回拒绝结果
**验证:** `pytest tests/watchlight/test_scheduler_service.py -q` 绿;lint 过

## T11: 频率边界与触发链路

**文件:** `backend/src/watchlight/scheduler/service.py`(补充)、`loop.py`
**依赖:** T10, T6
**步骤:**
1. `service.trigger_now(user_id, task_id) -> execution_id`:插入 pending execution 且 `triggered_by=manual`;**不破坏后续周期计划**(当前周期 scheduled_at 不动,F4)
2. `loop.SchedulerLoop.tick(now)`:扫 executions.status=pending AND scheduled_at<=now AND watch_tasks.status=active;同一 task_id 已存在 running 跳过并写 events 记 "skipped overlap"(F4)
3. CAS pending→running:在事务内 `UPDATE executions SET status='running', started_at=?, heartbeat_at=? WHERE execution_id=? AND status='pending'`,影响行数为 0 时视为已被消费或 CAS 失败,放弃该次
4. `tick` 内调用 collector(占位,实际 collector 注入由 T22 提供)
5. 写测试:模拟同 task 两个到期 pending,只一个转 running;手动触发的 pending 不影响原周期下次 scheduled_at
**验证:** `pytest tests/watchlight/test_scheduler_loop.py -q` 绿;lint 过

## T12: Scheduler 重启恢复(F12 / AC18)

**文件:** `backend/src/watchlight/scheduler/loop.py`(补充)
**依赖:** T11
**步骤:**
1. `SchedulerLoop.recover(now, heartbeat_timeout=600)`:SELECT executions WHERE status='running' AND heartbeat_at < now - timeout
2. 对每条:写 `status='recovered'`,把原 `running` 作为 status_history 第一条追加,`ended_at=now`,failure_summary="recovered by boot"
3. recover 后这些 execution 不再被 tick 重取;原 task 由下一周期生成新 pending(若 active)
4. 写测试:手工插入 running execution、heartbeat 远古,调用 recover 后状态为 recovered,且 status_history 含原 running
**验证:** `pytest tests/watchlight/test_scheduler_recover.py -q` 绿;lint 过

## T13: Collector 源展开 + robots + 沙盒

**文件:** `backend/src/watchlight/collector/expander.py`、`robots.py`、`fetch.py`、`content_guard.py`
**依赖:** T6
**步骤:**
1. `expander.SourceExpander.expand(source_scope) -> list[SourcePlan]`:URL 直接成 item;关键词走 SearchProvider 接口(注入,默认走现有 web_search provider 抽象)
2. `robots.RobotsCache.is_allowed(url)`:取 host robots.txt,接口失败默认拒绝?——按安全保守,失败先按 `allow`(否则正常站点 robots 一时不可达就误屏蔽);但显式 `Disallow: /` 路径必须置 blocked
3. `fetch.FetchClient` 抽象 + `HttpxFetchClient` 默认实现:User-Agent 可识别不伪装浏览器(N11);对 429/Retry-After 退避(N12)
4. `fetch` 在请求前调用 `tools.sandbox.policy.is_safe_url`,拒绝本机/内网/云元数据(N1、AC14)
5. `content_guard.classify(content, http_status) -> ContentKind{target|login_wall|captcha|paywall|error_page}`:命中非 target 时 SourceHit.status=blocked 且不写有效变化(F5)
6. 写测试:robots.txt 明确禁止 → blocked;sandbox URL 黑名单 → blocked;429 + Retry-After 后退避按参数生效
**验证:** `pytest tests/watchlight/test_collector_fetch_guard.py -q` 绿;lint 过

## T14: Collector 快照与错误分类

**文件:** `backend/src/watchlight/collector/snapshot.py`、`errors.py`
**依赖:** T13
**步骤:**
1. `snapshot.SnapshotWriter.write(snapshot_data) -> SnapshotRecord`:计算 normalized content 的 SHA256 `content_hash`;若与上一条 same `source_url` 的 content_hash 一致 → 写 SourceHit.status=unchanged 且**不写 snapshot 行**(F5 不重复快照)
2. changed → 写新 snapshot 行 + blob raw + blob normalized + previous_snapshot_id 链接(F5)
3. `errors.ErrorClassifier.classify(exception|http_status) -> ErrorCode`:瞬时网络/解析/限流不可访问/不可恢复 五类按 N12 表
4. 错误分类落到 SourceHit.error_code + retry_count,瞬时网络错误最多 3 次指数退避(5s→60s);解析错误 same execution 内不再尝试同源(N12)
5. 写测试:重复抓相同内容只产 1 个 snapshot;登录页 content_guard 命中后 SourceHit.status=blocked 不写 effective snapshot;网络错误计数到上限后置 unreachable
**验证:** `pytest tests/watchlight/test_collector_snapshot_errors.py -q` 绿;lint 过

## T15: Collector runner 编排 + 限速

**文件:** `backend/src/watchlight/collector/runner.py`
**依赖:** T14
**步骤:**
1. `Collector.run(execution_id)`:展开来源 → 按 host 分组,同 host 串行、间隔≥2s,跨 host 整体并发(可任意io 多路,但全局并发上限 ≤ config.max_concurrent_fetches,默认 4)(F5、N11)
2. 每源完成更新 SourceHit 与 execution.heartbeat_at
3. 所有源完成或被取消后,聚合统计:source_count/change_count(此时 0,由 analyzer 后填),execution.status → partial/failed/succeeded 基础判断(部分失败→partial,全部失败→failed);最终 status 留 analyzer 完成后再 settle(T17)
4. 单源超时上限(max_fetch_seconds,默认 30s)超时取消,不计入全局阻塞(N3)
5. 写测试:多 host 并发;同 host 间隔≥2s;单源超时不影响其他源完成
**验证:** `pytest tests/watchlight/test_collector_runner.py -q` 绿;lint 过

## T16: Analyzer 变化检测 + 去重

**文件:** `backend/src/watchlight/analyzer/change.py`、`dedupe.py`
**依赖:** T6
**步骤:**
1. `change.ChangeDetector.diff(prev_normalized, curr_normalized) -> list[Change]`:用文本分块+结构标签过滤广告/时间戳/布局噪声(F6);输出 added/removed/modified + uncertainty_level
2. `dedupe.CrossSourceDeduper.merge(signals, time_window)`:同实体/标题相似度≥阈值/同任务时间窗内合并;保留各原始 source_urls 不丢失(F6、AC6)
3. `DedupWindow(72h)`:查 signals WHERE task_id=? AND status IN (notified, proposed) AND captured_at >= now-72h,按 `dedup_key` 命中 → 新 signal status=deduped(F9、AC7)
4. 不确定变化 uncertainty_level=high → status=proposed 但不得进即时通知(T17 输出 sendable=false)
5. 写测试:仅广告变化不产 change;两源描述同事件合并为 1 个 signal 且 source_urls 保留两者;72h 内同 dedup_key 命中之新 signal status=deduped
**验证:** `pytest tests/watchlight/test_analyzer_change_dedupe.py -q` 绿;lint 过

## T17: Analyzer 价值判断 + 简报(降级)

**文件:** `backend/src/watchlight/analyzer/value.py`、`brief.py`、`degrade.py`、`runner.py`
**依赖:** T16, T6
**步骤:**
1. `value.PreferenceFilter.apply(task_version, preferences, change) -> Verdict`:relevance/importance/novelty/source_credibility/uncertainty_level;未提供偏好时保守过滤(F7)
2. `brief.BriefBuilder.build(signal_ids, model_provider) -> Brief`:调 ModelProvider 注入接口(N6),facts/inferences/next_steps 分离,标注不确定性(F8)
3. 缺失 source_refs 或 captured_at 时 sendable=false(AC8);uncertainty=high 时 sendable=false(N4)
4. `degrade.handle(model_error) -> BriefStatus`:模型不可用→write brief 且 sendable=false + 标 failure_summary(不伪造,F8/F12/N6)
5. `runner.Analyzer.run(execution_id)`:读 Snapshot+Change → 产 Signal + Brief → 更新 execution.signal_count、execution.status 最终 settle(succeeded/partial/failed)
6. 写测试:无偏好时 verdict 保守;简报缺失 source_refs 时 sendable=false;模型 provider 返回错误时 brief sendable=false 且 execution 状态收敛;冲突来源不被隐藏(简报出现矛盾标注)
**验证:** `pytest tests/watchlight/test_analyzer_value_brief.py -q` 绿;lint 过

## T18: Notifier 免打扰 + 去重 + 重试

**文件:** `backend/src/watchlight/notifier/dnd.py`、`dedup.py`、`channels.py`、`queue.py`
**依赖:** T6
**步骤:**
1. `dnd.DoNotDisturbCalculator.next_send_at(user_id, now) -> time_or_none`:按用户时区(N10)计算,跨零点/夏令时边界靠用户当前时区;返回 None 表示立即可发(AC16)
2. `dedup.DedupGate.check(signal_id, channel_key) -> allow|already_sent`:查 deliveries 表,同 signal 同 channel 跨渠道总发送数≤已绑定渠道数(F9)
3. `channels.ChannelAdapter` 抽象 + web/feishu 出站实现(沿用现有 channels 出站能力,N5)
4. `queue.enqueue(brief_id, signal_ids) -> DeliveryPlan`:写 `deliveries` status=queued(若 DnD 命中立即 status=deferred 并写 scheduled_send_at)
5. `queue.drain_due(now)`:扫 deferred AND scheduled_send_at<=now,逐条 sending→delivered/failed;失败按 N12 表退避有限重试;不可恢复置 failed
6. 写测试:DnD 时段内非紧急 → deferred;dnd 结束后发送;同 signal 同 channel 第二次 enqueue → suppressed 跨渠道超额;模拟网络错误 2 次重试后 delivered
**验证:** `pytest tests/watchlight/test_notifier.py -q` 绿;lint 过

## T19: Feedback 偏好(作用域严格)

**文件:** `backend/src/watchlight/feedback/service.py`、`preferences.py`、`export.py`
**依赖:** T6
**步骤:**
1. `service.submit(user_id, delivery_id, rating, reason=None) -> feedback_id`:写 feedbacks 表;rating ∈ {useless, useful, too_frequent}(N7)
2. `preferences.map_feedback(feedback) -> Preference`:合成 include/exclude/frequency_cap,**scope 严格 task_id**(F10、AC17),写 preferences 且 `created_from_feedback_id`
3. `preferences.list_for_task(user_id, task_id) -> PreferenceView[]`:含 `applies_to`/`originating_feedback_id`,可见可枚举(F10)
4. `preferences.revoke(user_id, preference_id)`:soft revoke(`revoked_at`),不回改已交付简报(N14)
5. `preferences.apply_filter(task_id, change) -> include|exclude|score_adjust`:T17 调用
6. `export.export_user_data(user_id) -> dict`:导出任务/历史/反馈/偏好(AC13);不含凭据明文,由 observing.redact 过一遍
7. 写测试:单次 too_frequent 不永久屏蔽整主题/整来源(只生成一条 frequency_cap preference,撤销后下一 execution 不再受影响);preferences 表不存在跨用户写入路径(尝试用 B 用户写 A 任务的 preference 会被拒绝)
**验证:** `pytest tests/watchlight/test_feedback.py -q` 绿;lint 过

## T20: Observing 事件/指标/追溯/脱敏

**文件:** `backend/src/watchlight/observing/events.py`、`metrics.py`、`trace.py`、`redact.py`
**依赖:** T6
**步骤:**
1. `events.emit(event_dict)`:必含 execution_id/task_id/user_id;落 events 表追加写
2. `metrics` counters:`task_run_success_rate/source_fail_rate/signal_yield_rate/delivery_success_rate/duplicate_delivery_rate/feedback_count`(N8),由各层在状态终态时 emit 后再由 metrics 聚合
3. `trace.trace_delivery(delivery_id) -> Trace`:从 deliveries → brief_ids → signal_ids → change_ids → source_hits → snapshots,返回分层结构(F11、AC11)
4. `redact.Redactor.redact(dict, spec) -> dict`:按 config.redact_sensitive 规则脱敏凭据/敏感字段(N1、N4)
5. 写测试:emit 缺少 task_id 抛错;trace 链路自下而上可追溯到 snapshot_id 和 captured_at;redact 把密钥字段值替换为 `[REDACTED]`
**验证:** `pytest tests/watchlight/test_observing.py -q` 绿;lint 过

## T21: Gateway REST methods

**文件:** `backend/src/watchlight/gateway/methods/watch_{tasks,exec,signals,delivery,identity}.py`
**依赖:** T10, T11, T18, T19, T20
**步骤:**
1. `watch_tasks`:POST/GET/PATCH/DELETE 任务,POST 必须先 create 返 normalized_summary,再 POST /confirm 才激活(F2)
2. `watch_exec`:GET 任务执行时间线 + 单 execution 详情(F11)
3. `watch_signals`:GET 简报 + GET /trace?delivery_id=... 返回追溯链路
4. `watch_delivery`:GET 通知历史 + POST /feedback(rating/reason)
5. `watch_identity`:POST /binding/start、POST /binding/confirm、POST /unbind/start、POST /unbind/confirm;必须基于已解析的 user_id(act、二次确认强校验)
6. 所有 handler 用 IdentityRegistry 从请求中解析 user_id,未授权直接 401(AC1)
7. 写测试:两 user 互相取任务返回 403;trace 接口可达;确认绑定返回新 user_id
**验证:** `pytest tests/watchlight/test_gateway_methods.py -q` 绿;lint 过

## T22: Boot 注入与 loops 启动

**文件:** `backend/src/watchlight/gateway/boot_watchshed.py`(新建)、`gateway/boot.py`(修改)、`gateway/app.py`(修改)
**依赖:** T15, T17, T18, T20, T21
**步骤:**
1. `boot_watchshed.bootstrap(app_state, config) -> StartedLoops`:
   - `Store.open(config.watchshed.db_path)`、`migrate(store)`
   - 构造 IdentityRegistry / TaskService / SchedulerLoop / Collector / Analyzer / Notifier / FeedbackService / Observing,注入各自 Provider(从 extensions 装配 ModelProvider/SearchProvider,沿用现有 gateway 装配方式)
   - `SchedulerLoop.recover(now)` 一次
   - anyio taskg 起两个循环:`scheduler_tick_task`(每 30s)和 `notifier_drain_task`(每 30s),并在 app 关闭时取消
2. `boot.py` 在装配 stage 调 `boot_watchshed.bootstrap`,把 StartedLoops 放入 AppContext 供 method 共享
3. `app.py` 注册 `watch_*` 路由(对应 T21 的 handlers),挂到 `/api/watch/*` 下
4. 写测试:调用 `bootstrap` 后 `SchedulerLoop.tick` 跑一次不再异常;`/api/watch/tasks` GET 在 mock user 下返回 200
**验证:** `pytest tests/watchlight/test_boot.py -q` 绿;lint 过

## T23: 固定来源样本 + AC14 端到端

**文件:** `fixtures/watchlight/sources/*`、`fixtures/watchlight/expected/*`、`tests/watchlight/test_e2e.py`、`tests/watchlight/conftest.py`
**依赖:** T22
**步骤:**
1. 在 `fixtures/watchlight/sources/` 放 3 个静态 HTML 文件(v1 含某产品介绍,v2 新增 "v2.0 released",v3 改价格)和 `pages_manifest.json`(对应 source_url → 文件)
2. `conftest.py` 提供 `frozen_time` fixture(`freezegun` 或自实现 fake clock 传给 SchedulerLoop/Notifier)和 `fixed_store` fixture(打开 tmpdb 并 migrate,预置一个 user + 绑定渠道)
3. E2E 测试步骤:
   a. `TaskService.create(user, draft)` 指向固定 source URL(用 file:// 模式由 FetchClient 测试桩返回 fixture 内容),normalize 返回 missing=[] 时 `confirm` 激活
   b. 推进时间到 scheduled_at,`SchedulerLoop.tick` → `Collector.run` 抓 v1 → 写 snapshot,status=ok,execution 初始
   c. 改动 fixture 内容为 v2,再推进一个周期 tick → Collector 检测到 changed → Analyzer 产出 Signal + Brief 且 sendable=true
   d. `Notifier.drain_due` → Delivery delivered
   e. `trace.trace_delivery` 返回 delivery→brief→signal→change→snapshot→source_url 链
   f. `FeedbackService.submit(useless)` 生成 preference 且下一 execution `apply_filter` 生效
   g. 单源错误案例:再改 fixture 为 login 页 HTML → SourceHit.status=blocked 不产 Signal
4. 时区场景:同一 user 两个渠道时区不同,渲染 next_send_at 时区差异正确但调度比较 UTC 不重复执行(AC16)
5. 反向验收:在 TaskService 提交违法监控目标(命中 spec 10 反向清单)→ 返回 unsupported_action 不入库(AC15)
**验证:** `pytest tests/watchlight/test_e2e.py -q` 绿;`pytest tests/watchlight -q` 全量绿;`ruff check .` 绿;`mypy backend/src` 绿

## T24: 飞书/Web 入站 remember: TaskService 触达(自然语言创建)

**文件:** `backend/src/watchlight/channels/feishu/plugin.py`、`webchat/plugin.py`(修改,只补自然语言入口)
**依赖:** T22
**步骤:**
1. 入站消息经 T9 resolve 后,若消息包含意图关键词如"创建关注"/"关注",在 plugin 中转调 TaskService.normalize(user_id, draft_text);2 轮内补齐缺失字段,否则切换到表单提示(F2)
2. 自然语言创建的 draft normalize 不达置信度时,回显规范化摘要并请求 confirm,confirm 后才生成 task(F2)
3. 单次负面反馈不直接置全局屏蔽,通过 T19 的偏好链路处理
4. 写测试:模拟两轮自然语言对话创建任务的会话转换,最终一条确认后任务被创建
**验证:** `pytest tests/watchlight/test_channels_nl_create.py -q` 绿;lint 过

## 执行顺序

```
T1 ─┬─ T2 ─┬─ T3 ─┬─ T5 ─┬─ T10 ─┬─ T11 ─ T12 ─┐
    │       │       │       │       │           │
    │       │       │       ├─ T4   │           │ (collector 注入由 T22)
    │       │       │       │       │           │
    │       │       ├─ T6 ─┬─ T13 ─ T14 ─ T15 ─┤
    │       │       │       │       │           │
    │       │       │       ├─ T16 ─ T17 ─┐    │
    │       │       │       │              │    │
    │       │       │       ├─ T18 ────────┤    │
    │       │       │       ├─ T19 ────────┤    │
    │       │       │       └─ T20 ────────┤    │
    │       │       │                       │    │
    │       │       └─ T7 ─ T8 ─ T9 ────────┤    │
    │       │                                │   │
    │       └────────────────────────────────┴── T21 ─ T22 ─ T23 ─ T24
```

简化依赖含义:

- T1→T2→T3 为 storage 地基,所有仓储任务(T4~T7)依赖 T3
- T8/T9 为 identity 与渠道接入,可与 T5~T7 并行
- T10~T12 串行(scheduler 内部递进)
- T13→T14→T15 collector 串行
- T16→T17 analyzer 串行
- T18 notifier、T19 feedback、T20 observing 可并行的三个独立块
- T21 (REST) 必须等以上模块接口齐
- T22 (boot) 汇总所有,跑通最小链路
- T23 (E2E) 验证整链
- T24 (自然语言入口) 收尾

---

## 自检(plan.md 覆盖核对)

- [x] storage: T1~T7 / T4 / T3 覆盖
- [x] identity: T7 / T8 / T9
- [x] scheduler: T5 / T10 / T11 / T12
- [x] collector: T13 / T14 / T15
- [x] analyzer: T16 / T17
- [x] notifier: T18
- [x] feedback: T19
- [x] observing: T20
- [x] REST 与 boot: T21 / T22
- [x] 端到端与反向验收: T23 / T24
- [x] 每个任务有验证方式(单元测试或命令观察)
- [x] 依赖链无环

## T25: 用户回复摘要与飞书 Markdown 渲染

**文件:** `backend/src/watchlight/scheduler/nl.py`、`channels/feishu/client.py`、`channels/feishu/plugin.py`、对应测试
**依赖:** T24
**步骤:**
1. 将 normalized summary 转为中文字段、频率和渠道名称，确认回复不暴露 dict/JSON/internal key
2. 飞书出站默认发送 interactive markdown card，支持标题、强调、列表和链接
3. 卡片 API 返回失败时回退到纯文本发送，避免消息丢失
4. 增加摘要格式与飞书请求 payload 测试
**验证:** `pytest tests/watchlight/test_channels_nl_create.py tests/watchlight/test_feishu_rendering.py -q` 绿;lint 过

## T26: Web Markdown 安全渲染

**文件:** `frontend/src/components/MarkdownContent.vue`、`frontend/src/utils/markdown.ts`、`RuntimeTimeline.vue`、`MessageContextPanel.vue`
**依赖:** T25
**步骤:**
1. 解析常用 Markdown 为结构化 block/inline 节点，不使用不受控 `v-html`
2. 模型流式输出、通道回写和 assistant 上下文统一使用渲染组件
3. 仅允许 http/https 链接，HTML 与未知语法按文本显示
4. 为亮色工作台补齐标题、列表、引用、链接和代码样式
**验证:** `vue-tsc` 与 Vite build 通过；示例 Markdown 在 Web 工作台显示为富文本
