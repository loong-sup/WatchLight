# Watchlight

> 守望值得关注的，只让重要变化抵达。

Watchlight 是一个本地运行的个人情报追踪与决策助理。用户可以通过 Web 工作台或飞书创建关注任务；系统会按计划采集公开信息、保存历史快照、识别有价值的变化，并把带来源的决策简报发送到指定渠道。

项目同时保留了一套多模型 AI Gateway：统一管理会话、模型、工具调用、渠道消息和运行事件，方便在本地观察一条消息从入口到模型、工具和回复的完整链路。

当前版本为 `0.1.0`，仍处于开发阶段。

## 当前能力

- 关注任务：创建、确认、查询、修改、暂停、恢复、立即触发和安全删除。
- 自然语言任务流程：支持在 Web 与飞书中创建、补充、纠正、查询和删除关注任务。
- 情报处理链路：定时调度、网页采集、快照留存、变化检测、信号去重、价值判断和简报生成。
- 通知与反馈：免打扰、去重、重试、用户反馈、偏好记录和运行指标。
- 身份隔离：渠道身份绑定到统一用户，任务、执行记录和查询按用户隔离。
- Web 工作台：查看会话、模型输出、工具调用、消息上下文和七层运行链路。
- 飞书接入：私聊、群聊 `@机器人`、长连接收取消息，以及飞书云文档读写。
- 模型供应商：DashScope、OpenAI、Anthropic 和 DeepSeek，按环境变量中的可用密钥自动注册。
- 内置工具：网络搜索与网页读取、文件与 Shell 操作、会话协作、记忆搜索、飞书文档等；工具权限按运行场景限制。
- 可观测性：健康检查、诊断、结构化事件、指标，以及任务到通知的 trace 查询。

## 系统结构

```text
Web / 飞书
    │
    ▼
Gateway 与身份层
    ├── 会话、模型、工具调用
    └── 自然语言任务流程
              │
              ▼
任务与调度 → 信息采集 → 变化分析 → 通知交付 → 反馈与偏好
              │             │            │
              └──────── SQLite、快照与审计记录 ────────┘
```

核心数据默认保存在本地：会话位于 Watchlight 状态目录，关注任务数据库和网页快照默认位于仓库下的 `.watchlight-state/`。

## 环境要求

- Python 3.11+
- Node.js 18+
- pnpm
- 至少一个受支持模型的 API Key

```bash
python --version
node --version
pnpm --version
```

若未安装 pnpm：

```bash
npm install -g pnpm
```

## 快速开始

以下命令均从仓库根目录执行。

### 1. 安装依赖

```bash
python -m pip install -e ".[dev]"
pnpm --dir frontend install
```

### 2. 创建本地环境文件

PowerShell：

```powershell
Copy-Item .env.example .env
```

macOS / Linux：

```bash
cp .env.example .env
```

编辑 `.env`，至少配置一个模型密钥：

```dotenv
DASHSCOPE_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
DEEPSEEK_API_KEY=
```

按需配置联网搜索与飞书：

```dotenv
BOCHA_API_KEY=

FEISHU_APP_ID=
FEISHU_APP_SECRET=
FEISHU_DOCS_BASE_URL=https://your-company.feishu.cn
WATCHLIGHT_FEISHU_DOCS_WRITE_ENABLED=false
```

`.env` 已被 Git 忽略，请勿提交真实密钥。

### 3. 启动 Gateway

```bash
watchlight gateway run --host 127.0.0.1 --port 18789
```

也可以使用模块入口：

```bash
python -m watchlight gateway run --host 127.0.0.1 --port 18789
```

检查服务：

```bash
curl http://127.0.0.1:18789/health
curl http://127.0.0.1:18789/api/models
curl http://127.0.0.1:18789/api/channels/status
```

### 4. 启动 Web 工作台

另开一个终端：

```bash
pnpm --dir frontend dev -- --host 127.0.0.1 --port 3000
```

打开 <http://127.0.0.1:3000/>。Vite 会把 `/api`、`/ws` 和 `/health` 代理到本地 Gateway。

代码走读页位于 <http://127.0.0.1:3000/walkthrough.html>，用于按链路了解消息入口、Gateway、Runtime、工具调用与飞书文档写入。

## 使用关注任务

在 Web 或飞书中可以直接发送自然语言。例如：

```text
创建关注 https://example.com/releases 出现 v2.0 released
每天检查，通过飞书通知
确认
```

创建过程中，系统会先返回规范化摘要；信息不完整时继续追问，只有确认后任务才会启用。还可以发送：

```text
目前创建了哪些任务
删除任务
```

删除操作会列出当前用户可删除的候选任务，需要选中唯一任务并明确回复 `确认删除`。任务随后进入 `draining`，停止产生新执行，待在途执行收敛后转为逻辑删除。

关注任务也提供 REST API：

```text
GET    /api/watch/tasks
POST   /api/watch/tasks
GET    /api/watch/tasks/{task_id}
POST   /api/watch/tasks/{task_id}/confirm
PATCH  /api/watch/tasks/{task_id}
DELETE /api/watch/tasks/{task_id}
POST   /api/watch/tasks/{task_id}/pause
POST   /api/watch/tasks/{task_id}/resume
POST   /api/watch/tasks/{task_id}/trigger
```

业务 API 要求用户身份。调用时传入已注册的 `X-Watchlight-User-Id`，或同时传入 `X-Watchlight-Channel` 与 `X-Watchlight-Channel-User` 让系统解析渠道身份。身份注册入口为 `POST /api/watch/identity/register`。

其他业务接口包括：

- `/api/watch/executions`：执行记录。
- `/api/watch/signals`：变化信号。
- `/api/watch/deliveries`：通知交付记录。
- `/api/watch/trace/{delivery_id}`：交付链路追踪。
- `/api/watch/metrics`：运行指标。
- `/api/watch/export`：用户数据导出。

## 飞书配置

项目提供了长连接示例配置：

```bash
watchlight gateway run \
  --config examples/watchlight.feishu.example.json \
  --host 127.0.0.1 \
  --port 18789
```

Windows PowerShell 可写为一行：

```powershell
watchlight gateway run --config examples/watchlight.feishu.example.json --host 127.0.0.1 --port 18789
```

飞书开放平台需要创建企业自建应用、开启机器人能力、配置消息与文档权限、订阅 `im.message.receive_v1`，并发布应用版本。完整步骤及排查方法见 [feishurunbook.md](feishurunbook.md)。

云文档写入默认关闭；确认应用权限与目标租户无误后，再设置：

```dotenv
WATCHLIGHT_FEISHU_DOCS_WRITE_ENABLED=true
```

## 配置与本地数据

配置文件支持 JSON / JSON5 和 `${ENV_VAR}` 环境变量替换。加载优先级为：

1. `gateway run --config PATH` 指定的文件。
2. `WATCHLIGHT_CONFIG_PATH` 指定的文件。
3. `~/.watchlight/watchlight.json`。

常用环境变量：

| 变量 | 用途 | 默认值 |
| --- | --- | --- |
| `WATCHLIGHT_STATE_DIR` | 会话与运行状态目录 | `~/.watchlight` |
| `WATCHLIGHT_CONFIG_PATH` | Gateway 配置文件 | `~/.watchlight/watchlight.json` |
| `DASHSCOPE_API_KEY` | DashScope 模型 | 空 |
| `OPENAI_API_KEY` | OpenAI 模型 | 空 |
| `ANTHROPIC_API_KEY` | Anthropic 模型 | 空 |
| `DEEPSEEK_API_KEY` | DeepSeek 模型 | 空 |
| `BOCHA_API_KEY` | Bocha 网络搜索 | 空 |
| `FEISHU_APP_ID` / `FEISHU_APP_SECRET` | 飞书应用凭证 | 空 |

关注任务子系统的默认配置：

```json5
{
  watchshed: {
    enabled: true,
    dbPath: ".watchlight-state/watchlight-mvp.db",
    blobRoot: ".watchlight-state/blobs",
    schedulerTickSeconds: 30,
    maxTasksPerUser: 20,
    maxConcurrentExecutions: 4,
    maxConcurrentFetches: 4,
    maxFetchSeconds: 30
  }
}
```

## 开发与验证

```bash
# 后端测试
python -m pytest tests/watchlight -q

# Python 代码检查与类型检查
python -m ruff check backend/src/watchlight tests/watchlight
python -m mypy backend/src/watchlight

# 前端生产构建
pnpm --dir frontend build
```

项目规格、实施计划和验收记录位于 [`docs/`](docs/)。

## 项目结构

```text
.
├── backend/src/watchlight/
│   ├── agents/          # Agent 编排、模型选择、运行时、Harness 与子 Agent
│   ├── analyzer/        # 变化检测、价值判断、去重、降级与简报
│   ├── channels/        # WebChat、飞书、Slack、Telegram、企微等渠道适配
│   ├── cli/             # Gateway、诊断、配置、会话、日志与备份命令
│   ├── collector/       # 来源扩展、网页抓取、robots 约束、内容保护与快照
│   ├── config/          # JSON/JSON5 加载、环境变量替换、默认值与验证
│   ├── contracts/       # Agent、渠道、配置、插件、协议与会话数据契约
│   ├── core/            # 路径、环境、日志和通用错误等基础能力
│   ├── extensions/      # Anthropic、DashScope、DeepSeek、Ollama 和 OpenAI 适配实现
│   ├── feedback/        # 用户反馈、偏好规则与数据导出
│   ├── gateway/         # FastAPI、REST、WebSocket、鉴权、启动与运行事件
│   ├── identity/        # 用户身份、渠道绑定与审计
│   ├── notifier/        # 通知队列、免打扰、去重、重试与渠道适配
│   ├── observing/       # 运行事件、指标、脱敏与交付链路追踪
│   ├── plugins/         # 插件发现、安装、市场索引与启用状态
│   ├── scheduler/       # 任务服务、自然语言流程、限额与调度循环
│   ├── secrets/         # 环境、文件和本地凭据密钥解析与存储
│   ├── sessions/        # 会话生命周期、Transcript、搜索、压缩与用量
│   ├── storage/         # SQLite、数据迁移、Blob 和业务 Repository
│   └── tools/           # 工具注册、权限、审批、沙箱与内置工具
├── frontend/
│   ├── src/api/          # REST 与 Gateway WebSocket 客户端
│   ├── src/components/   # 工作台面板、运行链路和消息组件
│   ├── src/stores/       # Pinia 运行状态
│   └── src/utils/        # Markdown 等前端通用工具
├── tests/
│   └── watchlight/       # 后端单元、集成与端到端测试
├── docs/                # 产品规格、计划、任务与验收清单
├── examples/            # 飞书等示例配置
├── fixtures/            # 测试页面、协议帧、插件清单和期望结果
├── .env.example         # 本地环境变量模板
├── feishurunbook.md     # 飞书接入与排障手册
└── pyproject.toml       # Python 包、依赖与工具配置
```

以下目录由开发或运行过程生成，不属于主要源码结构：

- `.watchlight-state/`：关注任务 SQLite 数据库、快照 Blob 和本地会话状态。
- `.uploads/`：本地上传的运行时用户数据。
- `.pytest-tmp/`、`.pytest_cache/`、`.mypy_cache/`、`.ruff_cache/`：测试和静态检查缓存。
- `frontend/node_modules/`、`frontend/dist/`：前端依赖和生产构建产物。
- `.agents/`、`.claude/`：本地 AI 开发工具配置与记录。

## 常见问题

**Gateway 启动后没有模型回复**

- 确认 `.env` 至少配置了一个模型 API Key。
- 请求 `/api/models`，确认对应供应商已注册。
- 运行 `watchlight doctor` 或访问 `/api/diagnostics` 查看诊断结果。

**Web 工作台显示未连接**

- 确认 Gateway 监听 `127.0.0.1:18789`。
- 通过 Vite 开发服务访问页面，不要直接双击 `index.html`。
- 检查 `/health` 和 WebSocket `/ws` 是否被代理。

**飞书能主动发消息，但收不到用户消息**

- 确认应用已发布最新版本。
- 确认事件订阅使用长连接并添加了 `im.message.receive_v1`。
- 检查应用可用范围、机器人能力和消息权限。

**飞书文档只返回 ID，没有可访问链接**

- 设置正确的 `FEISHU_DOCS_BASE_URL`，例如 `https://your-company.feishu.cn`。
- 确认应用拥有文档权限；需要写入时显式启用 `WATCHLIGHT_FEISHU_DOCS_WRITE_ENABLED=true`。

**关注任务没有按时执行**

- 确认 `watchshed.enabled` 未被设为 `false`。
- 检查 `.watchlight-state/watchlight-mvp.db` 是否可写。
- 查看 `/api/watch/executions`、`/api/watch/metrics` 与 Gateway 日志。

## 当前限制

- 项目尚未发布稳定版，配置和 API 仍可能调整。
- 首期完整接入渠道是 Web 与飞书；仓库中的其他渠道适配模块不代表已在当前 Gateway 启动流程中启用。
- 信息采集面向公开可访问页面；登录页、验证码、访问拒绝和明确禁止抓取的页面会被阻断，不应绕过站点限制。
- 生成的变化判断和决策建议应结合原始来源复核，不应直接用于高风险或不可逆操作。
