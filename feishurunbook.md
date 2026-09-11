feishu# Watchlight-Py 飞书接入操作文档

本文档用于把 `watchlight-py` 跑通到飞书机器人，并列出当前能用的能力边界。

## 1. 本地服务启动

### 1.1 安装依赖

```bash
cd watchlight-py
python -m pip install -e ".[dev]"
```

### 1.2 环境变量文件

本地密钥文件已经写入：

```text
./.env
```

当前包含这些变量：

```text
DASHSCOPE_API_KEY
TAVILY_API_KEY
FEISHU_APP_ID
FEISHU_APP_SECRET
FEISHU_VERIFICATION_TOKEN
FEISHU_ENCRYPT_KEY
WATCHLIGHT_FEISHU_INTERNAL_SECRET
WATCHLIGHT_FEISHU_DOCS_WRITE_ENABLED
FEISHU_DOCS_BASE_URL
```

### 1.3 启动网关

```bash
cd watchlight-py
watchlight gateway run --host 127.0.0.1 --port 18789
```

如果 `Watchlight` 命令没有安装到当前 shell，可以用：

```bash
python -m watchlight.cli.main gateway run --host 127.0.0.1 --port 18789
```

启动时会自动读取以下位置，前面的优先级更高：

```text
watchlight-py/.env
仓库根目录 .env
仓库根目录 process.md
```

当前推荐 DashScope 模型：`qwen3.6-max-preview`，用于更强的深度分析和多工具规划。需要外部资料时，模型应先调用 `web_search`，再用 `web_fetch` 打开关键来源，最后综合来源继续执行后续工具。若某段时间只追求“创建飞书文档”工具调用稳定性，可临时切回 `qwen-plus`。

服务启动后检查状态：

```bash
curl -sS http://127.0.0.1:18789/api/models
curl -sS http://127.0.0.1:18789/api/channels/status
```

正常情况下：

- `/api/models` 能看到已注册的大模型供应商模型，例如 DashScope 的 `qwen-*`。
- `/api/channels/status` 能看到 `feishu` 渠道，且账号为 `default`。
- 终端日志里能看到 `provider_registered`、`feishu_channel_started`、`feishu_event_subscriber_started` 等事件。

## 2. 飞书开放平台配置

### 2.1 创建企业自建应用

1. 打开飞书开放平台开发者后台：
   `https://open.feishu.cn/app`
2. 选择或创建一个企业自建应用。
3. 进入应用后，打开左侧的「凭证与基础信息」。
4. 获取并保存：
   - `App ID`：写入 `FEISHU_APP_ID`
   - `App Secret`：写入 `FEISHU_APP_SECRET`

### 2.2 开启机器人能力

1. 在应用后台打开「应用能力」。
2. 添加并启用「机器人」能力。
3. 设置机器人名称、头像和描述。

### 2.3 开通权限

至少开通这些权限：

```text
im:message
im:message.p2p_msg:readonly
im:message.group_at_msg:readonly
im:message:send_as_bot
```

飞书文档、云空间、知识库、电子表格、多维表格至少需要按实际使用范围追加：

```text
docx:document
docx:document:readonly
drive:drive
drive:drive:readonly
wiki:wiki
wiki:wiki:readonly
sheets:spreadsheet
sheets:spreadsheet:readonly
bitable:app
bitable:app:readonly
```

如果后续要支持图片、文件、群信息、用户信息，再追加：

```text
im:resource
im:chat
contact:user.base:readonly
```

开通权限后需要在「版本管理与发布」里创建新版本并发布，否则权限不会在线上生效。

### 2.4 配置事件订阅

当前推荐使用长连接模式：

1. 打开「事件与回调」或「事件订阅」。
2. 连接方式选择「使用长连接接收事件」。
3. 添加事件：

```text
im.message.receive_v1
```

Webhook 模式目前不是主流程。只有后续切换到 Webhook 模式时，才需要使用：

```text
FEISHU_VERIFICATION_TOKEN
FEISHU_ENCRYPT_KEY
```

### 2.5 发布并启用应用

1. 打开「版本管理与发布」。
2. 创建新版本。
3. 提交发布。
4. 如果企业需要审批，在飞书客户端里完成审批。
5. 发布完成后，在飞书客户端搜索机器人名称，打开机器人会话。

## 3. 飞书内测试方式

### 3.1 私聊测试

1. 启动本地网关。
2. 在飞书客户端搜索机器人名称。
3. 打开机器人私聊。
4. 发送：

```text
你好，介绍一下你自己
```

预期结果：机器人收到消息，调用模型生成中文回复，并在飞书里回复文本。

### 3.2 群聊测试

1. 把机器人添加进群。
2. 在群里发送：

```text
@机器人 帮我总结一下这个项目现在能做什么
```

默认策略下，群聊只有 `@机器人` 的消息会被处理。没有 `@` 的群消息会被忽略。

### 3.3 收不到消息事件时怎么排查

如果机器人能主动发消息，但用户发消息没有回复，先看网关日志：

- 有 `feishu_ws_connected`：长连接已经连上。
- 没有 `feishu_event_received` 或 `inbound_message`：飞书没有把消息事件推给网关。
- 有 `inbound_message` 但没有飞书回复：再查模型调用或 `feishu_reply_failed`。

最常见原因是权限或事件订阅没有在线上版本生效：

```text
im:message.p2p_msg:readonly       # 单聊消息事件
im:message.group_at_msg:readonly  # 群聊 @机器人 消息事件
im:message:send_as_bot            # 机器人发消息
```

补权限后必须「创建新版本并发布」。发布后保持网关运行，再到「事件与回调」确认：

1. 事件配置方式是「使用长连接接收事件」。
2. 已添加 `im.message.receive_v1`。
3. 开发者后台「日志检索 > 事件日志检索」里能看到这次消息事件。

### 3.4 本地事件接口测试

这个接口用于后续 sidecar 或本地模拟，不直接替代飞书长连接。启动网关后，在另一个终端执行：

```bash
cd watchlight-py
set -a
. ./.env
set +a

body='{"accountId":"default","eventType":"im.message.receive_v1","event":{"sender":{"sender_id":{"open_id":"ou_local_test"}},"message":{"message_id":"om_local_test","chat_id":"oc_local_test","chat_type":"p2p","message_type":"text","content":"{\"text\":\"本地飞书事件测试\"}"}}}'
sig=$(printf '%s' "$body" | openssl dgst -sha256 -hmac "$WATCHLIGHT_FEISHU_INTERNAL_SECRET" -binary | xxd -p -c 256)

curl -sS -X POST http://127.0.0.1:18789/internal/channels/feishu/events \
  -H "content-type: application/json" \
  -H "x-watchlight-signature: sha256=$sig" \
  --data "$body"
```

返回示例：

```json
{"ok":true,"handled":true}
```

如果模型或飞书网络不可用，事件入口仍可能返回成功，但终端日志里会看到模型调用或飞书回复失败的错误。

### 3.5 飞书文档测试

文档读取和搜索默认可用。可以在飞书里直接问：

```text
@机器人 搜索飞书文档里和 Watchlight 有关的内容
@机器人 读取这个飞书文档的正文：https://xxx.feishu.cn/docx/xxxx
```

创建、更新、删除文档属于写操作，默认被保护。确认权限和使用范围后，把 `.env` 改成：

```text
WATCHLIGHT_FEISHU_DOCS_WRITE_ENABLED=true
```

如果希望机器人回复可点击文档链接，可以额外配置企业云文档根域名：

```text
FEISHU_DOCS_BASE_URL=https://你的企业域名.feishu.cn
```

联网搜索使用 Tavily Search。需要在 `.env` 配置：

```text
TAVILY_API_KEY=你的 Tavily API Key
```

`web_search` 会优先调用 Tavily；如果没有配置 `TAVILY_API_KEY`，会降级到 DuckDuckGo HTML 搜索。`web_fetch` 用于打开公开网页并提取正文，不需要额外 key。

如果不配置，飞书创建接口可能只返回 `document_id`。机器人会把发送者加为文档协作者，用户可在飞书云文档里按标题搜索打开。

然后重启网关，再测试：

```text
@机器人 创建一个飞书文档，标题是 Watchlight 测试文档，正文写一段项目说明
```

含公式内容建议让机器人直接创建文档，不要把公式作为普通 Markdown 文本转发。当前 `feishu_docs_create_with_content`
会把 `$...$`、`\(...\)`、`$$...$$`、`\[...\]` 转成飞书新版文档的公式元素。

## 4. 当前支持的飞书功能

当前可用：

- 飞书私聊文本消息接入。
- 飞书群聊 `@机器人` 文本消息接入。
- 文本回复到飞书。
- 每个发送者独立会话。
- 会话 transcript 写入本地状态目录。
- DashScope、OpenAI、Anthropic 按环境变量自动注册。
- 联网搜索工具：`web_search`，优先使用 Tavily Search，适合深度探索、时效信息和事实核验。
- 网页读取工具：`web_fetch`，用于打开公开 URL，提取页面标题、摘要、正文和可选链接，适合在搜索后核验官方资料、论文页、文档页或 GitHub 页面。
- 飞书消息触发的 agent run 使用 `messaging` 工具策略，默认不允许危险本地工具。
- 内部签名事件接口：`POST /internal/channels/feishu/events`，用于 sidecar 或本地测试。
- 飞书文档 OpenAPI 通用工具：`feishu_docs_api`。
- 飞书文档纯文本读取：`feishu_docs_raw_content`。
- 飞书文档搜索：`feishu_docs_search`。
- 飞书文档创建：`feishu_docs_create`，需要 `WATCHLIGHT_FEISHU_DOCS_WRITE_ENABLED=true`。
- 飞书文档创建并写入正文：`feishu_docs_create_with_content`，会把飞书消息发送者加为协作者，并把 LaTeX 公式写成飞书公式元素。
- 飞书云空间文件夹清单：`feishu_docs_list_folder`。
- 通过 `feishu_docs_api` 覆盖 `docx`、旧版 `doc`、`drive`、`wiki`、`sheets`、`bitable`、`mindnote`、`slides` 和 `suite/docs-api` 下的云文档 OpenAPI。

当前不支持：

- 飞书图片、文件、音频、视频解析。
- 飞书消息卡片。
- 反应表情、已读回执、消息编辑。
- 完整 thread/topic 语义。
- 从飞书直接运行 shell、改文件、执行 Playwright。
- 生产级 Node/TypeScript 官方 SDK sidecar。
- 本地二进制文件上传/下载的安全沙箱封装。相关飞书 API 可通过 `feishu_docs_api` 发起任务，但直接读写本地文件需要单独设计目录白名单。

## 5. Shell 和 Playwright 能不能接

技术上可以接，但当前不建议直接开放给飞书用户。

原因是飞书是远程入口，一旦把 shell、文件写入、Playwright 浏览器自动化直接暴露给群聊或私聊，任何有权限发消息的人都可能触发本机操作。当前实现已经把飞书来源的运行限制为 `messaging` 工具策略，默认不会允许本地危险工具。

后续如果要接，需要单独做：

- 飞书用户 allowlist。
- 群聊和私聊分级权限。
- 命令白名单。
- 人工确认流程。
- 操作审计日志。
- 超时、并发和资源限制。
- 沙箱工作目录隔离。

建议第一阶段只跑通聊天、总结、问答、生成文本；第二阶段再加“受控工具调用”。

## 6. 后续扩展顺序

建议按这个顺序继续：

1. 真实飞书长连接稳定性测试。
2. 补齐飞书错误码和重连日志。
3. 增加飞书用户 allowlist。
4. 增加简单管理命令，例如 `/help`、`/status`、`/reset`。
5. 再考虑 shell、Playwright、文件写入等高风险工具。
