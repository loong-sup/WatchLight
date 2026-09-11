# 企业微信智能机器人接入

Watchlight 的 `wecom` 渠道使用企业微信“智能机器人 API 模式”，支持企业内部单聊和内部群聊中 `@机器人`。它不是只能单向推送的群 Webhook 机器人，也不是企业微信自建应用回调。

## 1. 创建机器人

1. 登录企业微信管理后台。
2. 进入“安全与管理 → 管理工具 → 智能机器人”。
3. 选择“API 模式创建”。
4. 生成并记录 `Token` 与 43 位 `EncodingAESKey`。
5. 机器人名称应与 `WECOM_BOT_NAME` 一致，以便移除群消息开头的 `@机器人名称`。

## 2. 配置 Watchlight

```dotenv
WECOM_TOKEN=后台生成的Token
WECOM_ENCODING_AES_KEY=后台生成的43位EncodingAESKey
WECOM_BOT_NAME=Watchlight
```

```powershell
watchlight gateway run --config examples/watchlight.wecom.example.json --host 0.0.0.0 --port 18789
```

## 3. 配置回调 URL

默认账号：

```text
https://你的公网域名/api/channels/wecom/events
```

多账号：

```text
https://你的公网域名/api/channels/wecom/{account_id}/events
```

地址必须能被企业微信通过公网 HTTPS 访问。保存时企业微信会发起 GET 验证；Watchlight 会校验签名、解密 `echostr` 并返回明文。业务消息使用 POST JSON 加密回调。

## 4. 回复机制与限制

Watchlight 收到回调后立即返回空包，把模型运行放入后台任务；完成后使用回调中的临时 `response_url` 发送 Markdown 回复。每个 `response_url` 只能使用一次且有效期为一小时，因此当前渠道不支持没有入站消息的任意主动推送。

群聊由企业微信只在成员 `@机器人` 时回调。Watchlight 的会话路由还会包含群成员 ID，因此不同成员不会共享私人会话记录。

图片、文件和视频目前只记录加密媒体地址并生成占位文本，尚未下载和解密媒体；文本、语音转文字和图文混排中的文本可以直接进入模型。

## 5. 排查

- `/api/channels/status` 中 `wecom` 应显示 `configured: true` 和 `running: true`。
- 回调保存失败时，确认后台与 `.env` 使用完全相同的 Token、EncodingAESKey。
- 公网反向代理不能改写查询参数或请求体。
- 智能机器人只能加入企业微信内部群，不能加入外部客户群或普通个人微信群。
