# Watchlight MVP Checklist

> 输入:`docs/spec.md` v0.4 + `docs/plan.md` + `docs/task.md`
> 规则:每一项通过运行代码或观察行为验证,聚焦系统行为而非实现;代码重构但行为不变时本文件仍然适用。
> 验证命令默认在仓库根 `D:\watchlight` 执行;每次先跑命令看实际输出,再下结论。

## A. 编译与基线

- [x] 安装后端开发依赖后,`python -m ruff check .` 无错误(验证:命令退出码 0)
- [x] `python -m mypy backend/src` 无错误(验证:命令退出码 0)
- [x] `python -m pytest tests/watchlight -q` 全量通过(验证:末行 `passed` 且无 `failed`)
- [ ] 前端 `pnpm --dir frontend build` 通过(验证:产出 `frontend/dist/index.html`)
- [x] Gateway 启动后 `/health` 返回 200(验证:`curl -sS http://127.0.0.1:18789/health` 响应非空)

## B. 状态模型一致性(AC18)

- [ ] 任务的状态只出现 `active|paused|deleted|draining` 四种字符串,在 DB、REST 响应、历史展示三处一致,不存在同义词混用(验证:用 sqlite3 cli 查所有 status 取值,REST 拉一份任务列表比对,前端历史页扫一遍)
- [ ] Execution 在 DB、REST、日志三处的 status 只出现 `pending|running|succeeded|partial|failed|cancelled|timed_out|recovered` 八种(验证:抽样触发各终态后查 DB 与接口)
- [ ] Signal status 只出现 `proposed|suppressed|notified|deduped|expired`,且每个 Signal 在 DB 中能查到一条可追溯的 status 流转记录而非黑盒(验证:对一个 notified Signal 查其 status 历史)
- [ ] 强制中止并重启 Gateway 后,任何原 `running` 状态的 Execution 被收敛为 `recovered` 或明确终态;DB 与接口中不再有 `running` 长期滞留(验证:杀进程前注入一条 running 的 Execution,重启后查其状态)
- [ ] SourceHit status 只出现 `ok|unchanged|changed|unreachable|unparseable|blocked`(验证:构造各场景后查 DB 取值集合)

## C. 身份与隔离(AC1,F1,N1)

- [x] 两个独立 user 各自创建任务后,任一方通过 REST / WebSocket / 历史查询接口尝试读取对方的 task_id 都得到 403 或 not found,不得返回数据(验证: User A 创建 task,用 User B 的凭证 GET 该 task_id 与列表)
- [ ] 两个 user 通过 REST `/api/watch/exec` 互查对方 task_id 的执行时间线被拒(验证:同上)
- [x] 未绑定渠道身份时 resolve 不返回任何已存在用户的数据;只有绑定确认成功后才能读到对应 user 的任务(验证:首次入站消息走 identity 解析,确认 DB 与日志里不出现他人 user_id)
- [x] 从未出现过的飞书身份首次发消息时自动创建独立用户并继续普通对话，不显示绑定拦截提示(验证:清空该 open_id 后发送“你好”，收到正常 agent 回复且 identity.status=bound)
- [x] pending 或已解绑的飞书身份不会被首次注册逻辑重新建号，且不能读取原用户数据(验证:分别构造 pending/unbinding 后再次入站，观察绑定提示且 users 数量不增加)
- [ ] 主渠道主动向用户回显 `UnbindImpact`(归属说明)后才允许确认解绑;未走该步骤直接 confirm_unbind 被拒(验证: POST `unbind/confirm` 不带前置 impact 的请求返回错误)
- [x] 绑定确认 token 在 TTL 之外失效;重复 token 不允许二次确认(验证: 用旧 token 再 confirm 返回错误)
- [ ] 解绑后,被解绑渠道的 channel_user_id 不能再读取原 user 的任务或历史(验证: 解绑后再用该渠道身份调用业务接口被拒)

## D. 任务与规范化(AC2,F2)

- [x] 用自然语言 draft 创建时缺频率或缺通知策略,系统返回 missing_fields 且**不落库**(验证: create 后即时查 DB,该 user 名下无新任务)
- [x] 缺失字段最多 2 轮询问未补齐时切换表单/终止创建,不静默启用(验证: 模拟两轮无补全对话,系统不再尝试第 3 轮,且无任务入库)
- [x] 在用户执行 `confirm` 之前 task.status ≠ active,且无对应 pending Execution 生成(验证: 只 create 不 confirm,查 task status 与 executions 表)
- [x] confirm 后立即生成首个 pending Execution,scheduled_at 等于创建时间 + frequency(验证: confirm 后查 executions 表)
- [ ] 修改任务条件后 task 表 version 自增,且历史条件可查;后续 Execution 的 task_version_id 指向当时生效的 version(验证: 修改前/后各跑一次执行,比对 task_version_id)
- [ ] 暂停后任务不再生成新 pending Execution;恢复后立刻有下一个周期 pending(验证: 暂停后人工推进 scheduler tick,无新 pending;恢复后再 tick,有新 pending)
- [ ] 删除单任务进入 draining,后续无新 pending;最终进入 deleted 后普通业务查询不再返回(验证: 触发删除后查 DB 状态流转与列表接口)

## E. 频率与调度(AC4,F4)

- [x] 自定义周期 < 900 秒 或 > 604800 秒 拒绝创建,不静默截断(验证: 提交 60 秒与 8 天的频率,create 返回错误)
- [ ] 启用任务按设定频率到期转为 running;`/api/watch/exec` 能正确展示上次和下次执行时间(验证: 推进时间至周期边界,tick 后查 execution 与接口)
- [ ] 同一 task_id 已存在 running 时,新一轮 tick 跳过并记录 "skipped overlap" 事件,不产生并发执行(验证: 注入长 running execution,推进时间触发 tick,观察事件表有 skipped 记录且无第二个 running)
- [x] 手动 trigger_now 生成的 Execution 不更新该任务下一周期 scheduled_at(验证: trigger 后比对周期 scheduled_at 未变)
- [ ] Gateway 重启后 active 任务仍在调度,其历史 pending 在表内存在(验证: 重启后推进时间,tick 仍能转 running)
- [ ] 达到每 user 任务上限再创建返回拒绝且不排队(验证: 把上限设为 1,创建第二个任务被拒)
- [ ] 达到全局并发上限的新 Execution 不被并发执行,且被观测层记录(验证: 设上限为 1,同时注入两个 pending,只有一个转 running)

## F. 来源与采集(AC3,AC5,F3,F5,N9,N11)

- [ ] 提交明显无效 URL(非 http/https、内网 IP、云元数据地址)被拒或置 blocked(验证: 用内网 IP 作为来源 URL,SourceHit.status=blocked)
- [ ] `tools/sandbox/policy` 拒绝的 URL 在采集层不会实际发请求(验证: 监听 fake fetch 客户端,被拒地址未触发请求)
- [x] 访问登录页/验证码页/付费墙时 SourceHit.status=blocked,且不写入"新版本快照",signals 表无对应有效变化(验证: 用 fixture 返回登录页 HTML,跑采集后查 snapshots 与 signals)
- [ ] robots.txt 显式 `Disallow` 的路径置 blocked,不绕过(验证: 用 fixture 站点 robots 返回禁用规则,跑采集比对 SourceHit)
- [x] 重复采集相同内容只产生 1 个 snapshot,且 SourceHit.status=unchanged(验证: 跑两次相同内容,第二次不新写 snapshot 行)
- [ ] HTTP 429 + Retry-After 命令被尊重,客户端不会立即重试(验证: 模拟返回 429+Retry-After:60,记录下次重试时刻 ≥ now+60)
- [ ] 同一域名并发请求数 ≤ 1,且相邻请求间隔 ≥ 2 秒(验证: 给同 host 3 个 URL,采集期间时间戳差 ≥ 2s)
- [ ] 单源超时上限触发后该任务其他来源仍能完成(验证: 注入一个会卡住的源 + 1 个正常源,跑采集,正常源 SourceHit.status=ok)

## G. 变化与去重(AC6,F6)

- [x] 测试页面仅改变广告/时间戳/布局不产生 Signal(验证: 用 fixture v1 与 v1' 比对,signals 表无新增)
- [ ] 仅正文关键内容变化产生对应 Change(added/removed/modified 之一)(验证: fixture v1 vs v2,changes 表新增一行)
- [ ] 两个来源描述同一事件时只产出 1 个对外通知,但 signals 表 source_urls 字段同时保留两个来源 URL,不被合并丢失(验证: 两源同事件跑链路,查 signal.source_urls 与 deliveries)
- [ ] 跨源合并保留合并依据(实体/标题相似度/时间窗),可在合并簇被回放时看到(验证: 查 signal 的 dedup/merge 元数据字段)
- [ ] 不确定变化在 Signal 上明确标记 uncertainty_level=high,且不进入对外即时通知(验证: 构造模糊变化,Brief.sendable=false)
- [ ] 默认去重窗口 72h 内同 task 同 dedup_key 的新 Signal status=deduped,不进通知(验证: 已通知一次信号,72h 内再造同 dedup_key,查新 signal.status)

## H. 价值判断与简报(AC7,AC8,F7,F8,N6)

- [ ] 命中 include 且不命中 exclude 的变化产出 Signal;不满足条件的变化有执行记录但无 Signal(验证: 用 trigger_condition 排除某关键词,fixture 命中该关键词时不产 signal,但 execution 仍有记录)
- [ ] 近期已 notified 且无新事实的相似 Signal 状态为 suppressed 或 deduped(验证: 已通知一次,72h 内再造,新 signal 非 notified)
- [ ] 判断记录可说明该 Signal 为何被保留或抑制(验证: 查 signal 与 events 表的 verdict/rationale)
- [ ] 对外简报同时包含:变化内容、重要性、来源链接、采集时间、可逆下一步建议(验证: 取一份 sendable=true 的简报肉眼核对五要素)
- [ ] 事实陈述与推断在简报中可被肉眼区分(验证: 肉眼读 brief,标 facts/inferences 分块)
- [ ] 多源相互矛盾时不被隐藏,简报中显示冲突(验证: 用 fixture 两源给出不同价格,Brief 必出现冲突标注)
- [x] 缺失 source_refs 或 captured_at 时 Brief.sendable=false(验证: 强制清空 source_refs 跑 builder,Brief sendable=0)
- [x] uncertainty_level=high 时 Brief.sendable=false(验证: 构造高不确定性 change,sendable=0)
- [ ] 简报不含金融/医疗/法律替代结论承诺(验证: 抽查几条对外简报文本)
- [ ] 模型 provider 失败时简报 sendable=false,execution 收敛到 failed/partial,brief 上有 failure_summary,不伪造成功(验证: 注入 ModelProvider 抛错,跑 analyzer 链路)

## I. 通知与反馈(AC9,AC10,F9,F10,N7,AC17)

- [ ] 同一 Signal 在同一 channel 只产生一次 delivered,第二次 enqueue 该同 channel 被 suppressed(验证: 对同一 signal 同 channel 连续 enqueue 两次,查 deliveries 第二条 status=suppressed)
- [ ] 同一 Signal 跨 channel 对外发送数 ≤ 已绑定 channel 数(验证: 1 个 user 绑定 web+feishu,signal 最多对外发 2 次)
- [x] 免打扰时段内非紧急通知 delivery.status=deferred,且 scheduled_send_at 在 DnD 结束之后(验证: 设 DnD 22:00-08:00,now=23:00,enqueue 后查 deferred)
- [ ] 免打扰结束后 deferred 通知被 drain_due 发送出去(验证: 推进时间到 08:30,tick 后该 delivery.status=delivered)
- [ ] 跨零点或夏令时切换边界仍按 user 当前时区延迟非紧急通知(验证: user 时区切换前后跑 DnD 计算,结果与 user 当前时区一致)
- [ ] 同 user 在两个不同时区渠道渲染 next_send_at 时不同,但调度比较基于 UTC,不产生重复或漏执行(验证: 两渠道时区 +8 与 -5,查接口返回的展示时间;另一执行同信号 task_id 在 DB 中只有一条 delivery)
- [ ] 修改 user 时区后,已存 Execution 的 UTC 原始时间不被改写,仅展示随之调整(验证: 修改前后查 DB `scheduled_at` 与 REST 返回的渲染值)
- [ ] 模拟出站发送失败按有限策略重试,最终结果写入 delivery.status,可在历史中看到 delivered 或 failed(验证: ChannelAdapter mock 连续两次抛错,gate 查 deliveries.status 为 failed 且 attempts 等于重试上限)
- [ ] Feedback 提交 useful/useless/too_frequent + reason 后能查到,并在下一 execution 应用对应偏好(验证: 提交 too_frequent,下一次 execution 跑 analyzer 时 apply_filter 生效)
- [x] Preference 视图可列举、可撤销;撤销后下一 execution 不再受其影响(验证: 列表查到 preference,撤销,再跑 execution,verdict 不变)
- [ ] 单次负面反馈不永久屏蔽整主题/整来源(验证: submit 一次 useless,后面再推同主题新事实仍能产 signal)
- [ ] 系统中不存在跨用户写入 preference 的路径:用 user B 提交 feedback 时显式指定 user A 的 task_id 应被拒(验证: 提交后查 preferences 表 user B 名下不出现 user A 的 task_id 行)
- [ ] 系统在用户未提供任何显式偏好与反馈前,筛选仅依赖任务自身条件(验证: 新 user 无偏好,analyzer 跑必须只受 trigger_condition 影响,events 中不出现画像迁移事件)

## J. 历史与追溯(AC11,F11,N4)

- [ ] 任务详情能展示每次 Execution 的开始/结束/状态/源数/变化数/信号数/通知数/失败摘要(验证: 拉一份执行详情比对字段齐全)
- [ ] 无有效变化的执行展示为 `succeeded` 且 signal_count=0,不展示为失败(验证: fixture 不变内容跑一次,查 execution.status)
- [ ] 失败 / 部分成功 / 取消 / 超时四种状态可见且不同(验证: 各场景逐一触发后查 execution)
- [x] 从 delivery_id 出发的 trace 链能层层回溯到 snapshot_id 与 captured_at(验证: 调用 trace 接口,逐层比对 ID)
- [ ] 面向用户的简报不暴露内部提示词或凭据(验证: 对外简报文本中搜索 prompt 模板片段与 API key,无命中)
- [ ] 失败可定位到所属阶段(collector/analyzer/notifier),但敏感内容被脱敏(验证: 构造 notifier 失败,events 表相关条目只含阶段标签 + 脱敏 error_code)

## K. 失败与恢复(AC12,F12,N2)

- [ ] 单源失败不阻断其他独立源,execution.status=partial 仍可能产出 signals(验证: 1 个坏源 + 2 个好源跑链路,signals 非空且 execution.status=partial)
- [ ] 临时网络错误按上限重试后停止,Subsequent execution 不再无限重试同源(验证: 持续返回 503,重试次数到上限后 SourceHit.status=unreachable,下一 execution 又重新开始计数)
- [ ] 不可恢复错误停止重试且 UI 上有可操作原因(验证: 注入 401 测试源,delivery SourceHit 状态与对外错误描述齐全)
- [ ] kill -9 Gateway 后重启,原 running Execution 进入 recovered,brief 不残留 running,且原 pending 周期不再被重复调度(验证: 杀进程 → 重启 → 推进时间 → tick,执行链路无重复 snapshot/signal/delivery)
- [ ] 重试与恢复过程中不产生重复 snapshot/signal/delivery(验证: 重启后查表 counts 与单一执行完毕后一致)

## L. 数据控制(AC13,F13)

- [ ] 用户能导出自己的任务/偏好/反馈(JSON)(验证: 调导出接口,肉眼核对内容齐全)
- [ ] 导出文件不含凭据明文(验证: 导出内容 grep `api_key|secret|token` 无命中)
- [ ] 申请删除全部个人业务数据后,普通业务查询不再返回该用户数据(验证: 删除后用该用户凭证调任意业务接口被拒)
- [ ] 删除后该用户任务不再被调度,也不产生通知(验证: 推进时间多次 tick 且 drain,该 user_id 无新 execution/delivery)

## M. 反向验收(AC15,第 10 节不做事项)

- [x] 提交"替我支付/转账/对外发公开内容"意图在 taskService 或入站对话层被明确拒绝,返回 unsupported_action 不入任务表(验证: 构造该 draft 提交,查响应与 tasks 表)
- [ ] 来源要求绕过登录/验证码/付费墙时该来源被置 blocked,signals 无对应有效变化(验证: source_scope 显式要求绕过登录,跑采集,SourceHit.status=blocked)
- [ ] 提交明显违法/高风险监控目标被拒(验证: 提交命中拒绝规则的 target,create 返回元数据拒绝,不入库)
- [ ] 用户尝试启用企业组织/团队空间/多智能体协商能力时,得到"首期不支持"反馈而非误导性成功(验证: 调用相关接口被明确拒绝,响应中无伪成功字段)

## N. 性能与成本(N3,N7)

- [ ] 创建/修改/暂停/恢复任务接口响应时间 P95 < 2s(验证: 用 `curl -w '%{time_total}'` 跑 10 次取分布)
- [ ] 任务列表 + 近期执行接口响应 P95 < 2s(验证: 同上)
- [ ] 单源慢调用不阻塞整任务,超时达到 max_fetch_seconds 被取消(验证: 慢源 60s,其他源在 max+5s 内完成)
- [ ] 用户创建任务时接口能展示执行频率与来源范围对使用量的预估影响(验证: create 响应包含 usage_estimate 字段)
- [ ] 达到额度上限后暂停新增消耗,并向用户说明恢复方式(验证: 逼近上限的新 Execution 被推迟或拒,events 与对外消息含恢复说明)

## O. 可观测与配置(N8,N13,N14)

- [x] 指标接口或日志可统计 task_run_success_rate、source_fail_rate、signal_yield_rate、delivery_success_rate、duplicate_delivery_rate、feedback_count(验证: 运行若干次执行后查 metrics/事件聚合,6 个指标均有非零或合理 0 值)
- [ ] 第三方来源持续不可用导致的失败在指标中被单独统计,不计入 task_run_success_rate 分子(验证: 持续 blocked 的源跑若干次,success_rate 与 source_fail_rate 各自分项正确)
- [ ] 配置换不同 ModelProvider 与 SearchProvider 后,系统行为不变,接口层不泄漏专有字段(验证: 切换 dashscope/openai 两套 provider 跑 E2E,简报字段与错误码一致)
- [ ] 删除 task 后的 deleted 状态保留期内普通业务查询不返回,但可通过审计层按脱敏方式访问(验证: 普通列表无 deleted task;审计专表查询可见)
- [ ] 任务每次条件修改可列出 version、修改人、修改时间,旧 version 不被原地覆盖(验证: 修改 3 次后历史链是 1→2→3 且无覆盖)
- [ ] Snapshot/Change/Signal/Brief/Feedback 均为追加写,不会被新数据原地覆盖(验证: 跑两次相同链接被改的简报,两次都各自留下不同 brief_id)

## P. 端到端场景

### P1: 完整正向闭环(spec 6.2 指定页面变化 + AC14)

- [ ] 准备固定 fixture 页面 v1(含产品介绍 + 价格),用户通过入站对话或 REST 创建"关注该页面价格变化,日报 + 重要变化即时通知"的任务,系统经过 normalize → 用户 confirm → 任务 active(验证: 任务存在、pending Execution 存在)
- [ ] 推进时间触发首次周期:采集 v1,SourceHit.status=ok,snapshot 写入,Brief 产但无变化故 signal_count=0,execution.status=succeeded(验证: 查 execution 与 signals)
- [ ] 替换 fixture 为 v2(改了价格字段),推进一个周期:产出 added/modified change、Signal(proposed)、Brief(sendable=true)(验证: change/signal/brief 三表联动)
- [ ] Notifier drain 后用户在两渠道(web + feishu)各收一条 delivered,trace 接口可从 delivery_id 走到 snapshot_id(验证: deliveries 各一条 delivered,trace 链路通)
- [ ] 用户对其中一条反馈 "useless" 并附 reason,后续同任务对同一价格不再产生即时通知但下次同类变化的偏好生效(验证: 提交反馈后,再造同事件,新 signal 被 suppressed/deduped)

### P2: 错误与边界(AC5 + AC12 子集)

- [ ] 同一 fixture URL 在某次返回登录页:SourceHit.status=blocked,本 execution 无新 signal(验证: 跑一次,查 source_hits 与 signals)
- [ ] 同一 execution 中 1 个源持续 503 + 2 个源正常:重试到上限后 SourceHit.status=unreachable,正常源的 Signal 仍产出,execution.status=partial(验证: 查 execution 与 signals)
- [ ] kill -9 模拟崩溃后重启,之前 running 的 execution 不再保留 running 状态,下一周期重新产出新 Execution(验证: 重启后查表)

### P3: 隔离与时区一致性(AC1 + AC16)

- [ ] A 与 B 两 user 同时跑各自关注任务,B 在任何渠道都看不到 A 的任务/历史/通知(验证: 端到端互查)
- [ ] 同一 user 在 web(时区 +8)与 feishu(时区 -5)渲染 next_send_at 不同,但实际发出的 delivery 只有一份(验证: 调两渠道列表接口 + DB deliveries count)

### P4: 模型/搜索可替换(N6)

- [ ] E2E 跑两遍,第一遍 dashscope 作为 ModelProvider、bocha 作为 SearchProvider,第二遍切换为 openai + 别的 SearchProvider mock,产物字段集与错误码一致(验证: diff 两次的 brief JSON schema 字段名集合)

## 自检

- [x] spec 对齐:AC1~AC19 每个 AC 都有对应条目;F1~F13、N1~N14 关键行为均被 B~O 节覆盖
- [x] 可观测:每条都是"做 X,看 Y";不存在"读代码核对实现"的条目
- [x] 与实现解耦:不引用具体文件名/类名;即便后续重组目录或重命名函数,条目仍适用
- [x] 端到端:含 4 个端到端场景(正向闭环、错误边界、隔离时区、模型替换)
- [x] 默认行为:每个任务步骤完成需要先跑命令取证再标记

## Q. 用户回复渲染

- [x] 任务确认回复以中文字段展示目标、来源、条件、频率和渠道，正文中不出现 `{'target':`、`frequency_seconds` 等内部表示(验证:飞书创建完整任务并观察确认消息)
- [x] 飞书中的标题、加粗、列表和链接由富文本卡片渲染，不显示 `**`、`#` 等 Markdown 源码(验证:检查 interactive payload 与飞书展示)
- [x] 飞书卡片发送失败时仍收到纯文本回复(验证:模拟 interactive API 失败后观察 text fallback)
- [ ] Web 工作台的模型输出、通道回写和 assistant 消息能渲染标题、强调、列表、链接与代码块，不显示常见 Markdown 源码(验证:发送固定 Markdown 示例观察三个展示位置)
- [ ] Web Markdown 不执行 `<script>` 等原始 HTML，且 `javascript:` 链接不可点击(验证:发送恶意示例后检查 DOM)
