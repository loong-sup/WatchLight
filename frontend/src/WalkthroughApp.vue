<template>
  <div class="walk-shell">
    <div class="grid-bg" aria-hidden="true"></div>

    <header class="topbar">
      <div class="brand">
        <span class="brand-mark"></span>
        <div>
          <p class="eyebrow">Watchlight FEISHU BOT WALKTHROUGH</p>
          <h1>从一条飞书消息读完整条代码链路</h1>
        </div>
      </div>
      <div class="top-tags">
        <span>TEACHING FLOW · 2026-04-26</span>
        <span>{{ activeIndex + 1 }} / {{ modules.length }}</span>
        <span>{{ activeModule.phase }}</span>
      </div>
    </header>

    <section class="scenario">
      <div>
        <p class="eyebrow">课堂主线</p>
        <h2>用户：帮我创建一个飞书文档：DeepSeek V4 的核心技术</h2>
      </div>
      <p>
        这节课只跟这一条消息走。先看程序怎么从 `main.py` 启动，再看飞书事件怎么被标准化，
        最后看模型如何调用搜索、抓取和飞书文档工具，并把文档链接发回给用户。
      </p>
    </section>

    <nav class="top-flow" aria-label="从 CLI 到飞书回复的完整脚本流程">
      <button
        v-for="(module, index) in modules"
        :key="module.id"
        :class="['flow-step', { active: index === activeIndex, done: index < activeIndex }]"
        type="button"
        @click="activeIndex = index"
      >
        <span class="step-no">{{ String(index + 1).padStart(2, '0') }}</span>
        <strong>{{ module.short }}</strong>
        <small>{{ module.fileShort }}</small>
      </button>
    </nav>

    <main class="workspace">
      <aside class="module-list">
        <div class="list-head">
          <p class="eyebrow">走读目录</p>
          <strong>按处理顺序点击</strong>
        </div>
        <button
          v-for="(module, index) in modules"
          :key="module.id"
          :class="['module-tab', { active: index === activeIndex }]"
          type="button"
          @click="activeIndex = index"
        >
          <span>{{ module.phase }}</span>
          <strong>{{ module.title }}</strong>
          <small>{{ module.file }}</small>
        </button>
      </aside>

      <section class="detail">
        <div class="detail-scroll">
          <section class="module-hero">
            <div>
              <p class="eyebrow">当前脚本</p>
              <h2>{{ activeModule.title }}</h2>
              <p>{{ activeModule.studentGoal }}</p>
            </div>
            <div class="position-box">
              <span>文件位置</span>
              <strong>{{ activeModule.file }}</strong>
              <em>{{ activeModule.symbol }}</em>
            </div>
          </section>

          <section class="story-board">
            <article class="story-main">
              <p class="eyebrow">先用白话理解</p>
              <h3>{{ activeModule.role }}</h3>
              <p>{{ activeModule.story }}</p>
            </article>
            <article class="story-side">
              <p class="eyebrow">这条飞书消息在这里</p>
              <p>{{ activeModule.exampleMoment }}</p>
            </article>
          </section>

          <section class="handoff-board">
            <article>
              <span>上一层交给它</span>
              <p>{{ activeModule.receivesFromPrevious }}</p>
            </article>
            <article>
              <span>这一层产出</span>
              <p>{{ activeModule.passesToNext }}</p>
            </article>
          </section>

          <section class="steps-board">
            <div class="section-head">
              <div>
                <p class="eyebrow">内部发生哪几步</p>
                <h3>把这一层拆开看</h3>
              </div>
              <code>{{ activeModule.phase }}</code>
            </div>
            <ol>
              <li v-for="step in activeModule.internalSteps" :key="step">{{ step }}</li>
            </ol>
          </section>

          <section class="io-board">
            <article>
              <span>输入是什么</span>
              <p>{{ activeModule.input }}</p>
            </article>
            <article>
              <span>核心处理</span>
              <p>{{ activeModule.process }}</p>
            </article>
            <article>
              <span>输出到哪里</span>
              <p>{{ activeModule.output }}</p>
            </article>
          </section>

          <section class="data-board">
            <div class="section-head">
              <div>
                <p class="eyebrow">数据在这里长什么样</p>
                <h3>{{ activeModule.dataTitle }}</h3>
              </div>
              <code>{{ activeModule.dataKind }}</code>
            </div>
            <pre><code>{{ activeModule.dataShape }}</code></pre>
          </section>

          <section class="code-board">
            <div class="section-head dark-head">
              <div>
                <p class="eyebrow">最后再看关键代码</p>
                <h3>{{ activeModule.symbol }}</h3>
              </div>
              <code>{{ activeModule.fileShort }}</code>
            </div>
            <p class="code-intro">{{ activeModule.codeIntro }}</p>
            <pre><code>{{ activeModule.code }}</code></pre>
          </section>
        </div>
      </section>

      <aside class="right-panel">
        <div class="right-scroll">
          <section class="checkpoint">
            <p class="eyebrow">你现在要抓住的重点</p>
            <h3>{{ activeModule.takeaway }}</h3>
          </section>

          <section class="checkpoint">
            <p class="eyebrow">容易误解</p>
            <p>{{ activeModule.commonMistake }}</p>
          </section>

          <section class="checkpoint">
            <p class="eyebrow">对象流转</p>
            <ul class="object-flow">
              <li v-for="item in activeModule.objectFlow" :key="item">{{ item }}</li>
            </ul>
          </section>

          <section class="checkpoint">
            <p class="eyebrow">自测问题</p>
            <ul>
              <li v-for="question in activeModule.questions" :key="question">{{ question }}</li>
            </ul>
          </section>

          <section class="checkpoint dark">
            <p class="eyebrow">全链路记忆</p>
            <p>
              CLI 负责把服务启动起来；飞书通道负责把外部事件翻译成内部消息；
              GatewayRuntime 负责统一调度；EmbeddedRuntime 负责模型和工具循环；
              文档创建是工具能力，最终回复只应该把链接送回飞书。
            </p>
          </section>
        </div>
      </aside>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

interface WalkModule {
  id: string
  phase: string
  title: string
  short: string
  file: string
  fileShort: string
  symbol: string
  studentGoal: string
  role: string
  story: string
  exampleMoment: string
  receivesFromPrevious: string
  internalSteps: string[]
  passesToNext: string
  input: string
  process: string
  output: string
  dataTitle: string
  dataKind: string
  dataShape: string
  codeIntro: string
  code: string
  takeaway: string
  commonMistake: string
  objectFlow: string[]
  questions: string[]
}

const modules: WalkModule[] = [
  {
    id: 'cli-main',
    phase: '启动',
    title: 'main.py 注册命令入口',
    short: 'main.py',
    file: 'backend/src/watchlight/cli/main.py',
    fileShort: 'cli/main.py',
    symbol: 'app.add_typer(...)',
    studentGoal: '你先确认一件事：程序入口只是把命令菜单搭起来，飞书消息还没有出现。',
    role: '它是整套命令行的目录页',
    story:
      '读 main.py 时不要急着找业务逻辑。这里像一个总目录，告诉 Typer：Watchlight 下面有 gateway、sessions、models 等命令。我们今天执行的是 gateway run，所以它的作用是把我们带到 gateway 这条分支。',
    exampleMoment:
      '“帮我创建文档”这句话此刻还不存在。当前只有一个人类在终端输入启动命令，系统还没有连上飞书。',
    receivesFromPrevious: '来自终端的顶层命令，比如 python -m watchlight gateway run。',
    internalSteps: [
      '创建 Typer 顶层应用，确定 CLI 名字叫 Watchlight。',
      '把 gateway_app 注册到 gateway 子命令下面。',
      '把 sessions、models 等旁支命令也注册进去。',
      '当用户选择 gateway run 时，Typer 会把控制权交给 cli/gateway.py。',
    ],
    passesToNext: '把 gateway run 这条命令路由到 cli/gateway.py 的 run 函数。',
    input: '终端命令，例如 python -m watchlight gateway run。',
    process: '创建 Typer app，并注册 gateway、sessions、models 等子命令。',
    output: 'gateway run 命令被挂到 CLI 上，下一步进入 cli/gateway.py。',
    dataTitle: '命令行入口',
    dataKind: 'CLI command',
    dataShape: `python -m watchlight gateway run

含义：
- Watchlight：顶层 CLI
- gateway：子命令组
- run：启动 Gateway 服务`,
    codeIntro: '这段代码只做命令注册。看它时重点问：gateway 这个子命令是在哪里挂进去的。',
    code: `app = typer.Typer(name="Watchlight")  # 创建顶层 CLI，后面所有子命令都挂在它下面
app.add_typer(gateway_app, name="gateway")  # 把 gateway 命令组挂进去，今天的启动链路从这里分叉
app.add_typer(sessions_app, name="sessions")  # session 管理命令，和本节主线无关
app.add_typer(models_app, name="models")  # 模型查看命令，和本节主线无关`,
    takeaway: 'main.py 是命令目录，不是服务启动器，也不是消息处理器。',
    commonMistake: '初学者容易在 main.py 里找飞书代码。这里不会有，因为飞书是 gateway 服务启动之后才会接入的。',
    objectFlow: ['终端字符串', 'Typer 命令路由', 'gateway run'],
    questions: ['这个文件有没有启动 FastAPI？', 'gateway run 下一步会进入哪个文件？'],
  },
  {
    id: 'cli-gateway',
    phase: '启动',
    title: 'gateway.py 把命令转成服务启动',
    short: 'gateway.py',
    file: 'backend/src/watchlight/cli/gateway.py',
    fileShort: 'cli/gateway.py',
    symbol: '@gateway_app.command("run")',
    studentGoal: '你要看到命令行参数如何变成一个可运行的 GatewayServer。',
    role: '它是从命令行世界进入服务世界的入口',
    story:
      'main.py 只是把你带到 gateway run，真正开始准备服务的是 cli/gateway.py。这里会读取 .env、加载配置、拿到端口和模型 key，然后创建 GatewayServer。可以把它理解成“启动前台”，先把开门需要的钥匙和地址准备好。',
    exampleMoment:
      '飞书用户还没有发消息，但 FEISHU_APP_ID、FEISHU_APP_SECRET、DASHSCOPE_API_KEY 会在这里被加载，为后面连接飞书和调用模型做准备。',
    receivesFromPrevious: 'Typer 解析后的 run 命令，以及 host、port、config_path、log_level 等启动参数。',
    internalSteps: [
      '读取 gateway 相关环境变量，确保飞书和模型 key 能被后续代码看到。',
      '加载 Watchlight 配置文件，得到通道、模型、工具等配置。',
      '用配置创建 GatewayServer。',
      '调用 server.run，让 uvicorn 开始运行 Web 服务。',
    ],
    passesToNext: '把已经加载好的 WatchlightConfig 交给 GatewayServer。',
    input: 'host、port、config_path、log_level 等命令行参数。',
    process: '加载 .env 和配置，创建 GatewayServer，然后调用 run。',
    output: '进入 gateway/server.py，准备创建 FastAPI app。',
    dataTitle: '启动参数',
    dataKind: 'CLI params',
    dataShape: `{
  "host": "127.0.0.1",
  "port": 18789,
  "config_path": "watchlight.feishu.json",
  "env": {
    "FEISHU_APP_ID": "...",
    "DASHSCOPE_API_KEY": "..."
  }
}`,
    codeIntro: '这段代码把“命令行参数”和“项目配置”合在一起，然后把服务对象创建出来。',
    code: `load_gateway_env()  # 先读 .env，飞书和模型配置之后都依赖这些环境变量
config = load_config(path=config_path)  # 再读 Watchlight 配置，确定启用哪些通道和工具
server = GatewayServer(config=config)  # 创建 GatewayServer，它负责包装 FastAPI 和 uvicorn
server.run(host=host, port=port)  # 开始监听端口，服务进入常驻运行状态`,
    takeaway: 'gateway.py 是启动胶水层，负责把 CLI 参数、环境变量和服务对象接起来。',
    commonMistake: '不要把 GatewayServer 当成 agent。它只是服务外壳，真正的模型执行还在后面的 runtime。',
    objectFlow: ['gateway run', '环境变量', 'WatchlightConfig', 'GatewayServer'],
    questions: ['为什么这里要加载 .env？', 'GatewayServer 是业务处理器还是服务包装器？'],
  },
  {
    id: 'server',
    phase: '启动',
    title: 'server.py 创建 FastAPI App',
    short: 'server.py',
    file: 'backend/src/watchlight/gateway/server.py',
    fileShort: 'gateway/server.py',
    symbol: 'GatewayServer.__init__',
    studentGoal: '你要把 server.py 理解成 Web 服务外壳，而不是业务主线。',
    role: '它负责把 Watchlight 放进 FastAPI 和 uvicorn 里运行',
    story:
      'GatewayServer 做的事情很朴素：拿到配置，确认端口，创建 FastAPI app，再交给 uvicorn。它像是把已经准备好的系统装进一个 Web 服务容器里，让外部可以通过 HTTP、WebSocket 或飞书长连接触达系统。',
    exampleMoment:
      '飞书请求还没有进来。当前只是把服务端口打开，等后续飞书长连接或前端 WebSocket 连上来。',
    receivesFromPrevious: 'cli/gateway.py 创建出的 WatchlightConfig 和启动端口。',
    internalSteps: [
      '保存配置对象，避免每个地方重新读配置。',
      '校验 Gateway 应该监听哪个端口。',
      '调用 create_app(config, boot=True) 创建 FastAPI app。',
      '用 uvicorn.run 把 app 挂到 host 和 port 上。',
    ],
    passesToNext: '把 config 和 boot=True 交给 gateway/app.py 的 create_app。',
    input: '已经加载好的 WatchlightConfig。',
    process: '校验端口，调用 create_app(config, boot=True)。',
    output: '得到可以被 uvicorn 运行的 FastAPI app。',
    dataTitle: '服务对象',
    dataKind: 'GatewayServer',
    dataShape: `GatewayServer
  config: WatchlightConfig
  port: 18789
  app: FastAPI(create_app(...))`,
    codeIntro: '这段代码要看的重点是 create_app。FastAPI app 是在那里创建的，boot=True 表示要启动完整 runtime。',
    code: `self.config = config or load_config()  # 保存配置；如果外面没传，就自己加载默认配置
self.port = validate_gateway_port(self.config)  # 从配置中确认 Gateway 端口
self.app = create_app(self.config, boot=True)  # 创建 FastAPI app，同时要求启动 watchlight runtime
uvicorn.run(self.app, host=host, port=actual_port)  # 交给 uvicorn 常驻运行`,
    takeaway: 'server.py 的职责是运行 Web 服务，不负责解释飞书消息。',
    commonMistake: '看到 server.py 很容易以为它是业务入口。实际上它只是把 app 跑起来，业务初始化在 app.py 的 lifespan 里。',
    objectFlow: ['WatchlightConfig', 'GatewayServer', 'FastAPI app', 'uvicorn'],
    questions: ['create_app 在哪个文件？', 'boot=True 会影响后续哪一步？'],
  },
  {
    id: 'app',
    phase: '启动',
    title: 'app.py 在生命周期里创建 GatewayRuntime',
    short: 'app.py',
    file: 'backend/src/watchlight/gateway/app.py',
    fileShort: 'gateway/app.py',
    symbol: 'create_app(...).lifespan',
    studentGoal: '你要看到 FastAPI 外壳和 Watchlight 系统中枢是怎么接起来的。',
    role: '它是 Web 框架和 watchlight runtime 的连接点',
    story:
      'FastAPI 有自己的生命周期，服务启动时会进入 lifespan。Watchlight 就借这个时机创建 GatewayRuntime。GatewayRuntime 是后面所有能力的中枢：模型、工具、通道、session、runtime event 都从这里统一调度。',
    exampleMoment:
      '这一步还没有用户消息，但会把前端 runtime 事件客户端挂进来。以后飞书消息、工具调用、模型输出都会通过这些事件展示到工作台。',
    receivesFromPrevious: 'server.py 传来的 config，以及 FastAPI 启动生命周期。',
    internalSteps: [
      '创建 GatewayRuntime，让系统有一个统一中枢。',
      '挂接 WebSocket 事件客户端池，让运行过程可以被前端看到。',
      '调用 boot，注册模型、工具、runtime 和通道。',
      '调用 start_channels，启动飞书这类需要长期等待外部事件的通道。',
    ],
    passesToNext: '把 config 交给 GatewayRuntime.boot，并在生命周期里启动所有通道。',
    input: 'FastAPI 服务启动事件。',
    process: '创建 GatewayRuntime，挂接前端事件客户端，调用 boot，再启动通道。',
    output: '系统准备好，可以接 WebChat 或飞书消息。',
    dataTitle: '应用生命周期',
    dataKind: 'FastAPI lifespan',
    dataShape: `FastAPI start
  -> GatewayRuntime(config)
  -> runtime.boot()
  -> runtime.start_channels()
  -> ready`,
    codeIntro: '这段代码说明了为什么 boot 不是某条消息触发的，而是服务启动时就执行。',
    code: `gateway_runtime = GatewayRuntime(config)  # 创建系统中枢，后面所有能力都挂在它下面
gateway_runtime.attach_event_clients(state.connected_clients)  # 让 runtime 事件可以推给前端页面
gateway_runtime.boot()  # 装配模型、工具、runtime、通道，此时还没有处理用户消息
await gateway_runtime.start_channels()  # 启动飞书等通道，让它们开始等待外部事件`,
    takeaway: 'app.py 把 FastAPI 的启动生命周期变成 Watchlight 的系统启动流程。',
    commonMistake: 'boot 后不是进入 WebSocket。WebSocket 是前端观察运行过程的一条连接；飞书消息走的是飞书通道。',
    objectFlow: ['FastAPI lifespan', 'GatewayRuntime', 'event clients', 'channels'],
    questions: ['GatewayRuntime 是什么时候创建的？', 'start_channels 属于启动阶段还是消息阶段？'],
  },
  {
    id: 'boot',
    phase: '启动',
    title: 'boot.py 装配模型、工具、通道',
    short: 'boot.py',
    file: 'backend/src/watchlight/gateway/boot.py',
    fileShort: 'gateway/boot.py',
    symbol: 'GatewayRuntime.boot',
    studentGoal: '你要理解 boot 是“装能力”，不是处理某条消息。',
    role: '它把系统需要的能力一次性登记到 runtime 上',
    story:
      'boot 的阅读顺序很重要：先不要看细节函数，而是看它在注册什么。模型供应商注册后，系统知道可用 qwen、openai 或 anthropic；工具注册后，模型能看到 web_search、web_fetch、feishu_docs；通道注册后，飞书消息才有入口。',
    exampleMoment:
      '用户还没说“创建文档”，但创建文档工具已经被登记好。后面模型判断需要写飞书文档时，才有工具可调用。',
    receivesFromPrevious: 'GatewayRuntime 自己持有的 config、环境变量和状态目录。',
    internalSteps: [
      '读取本地 session，恢复已有会话元数据。',
      '注册模型 provider，让系统知道有哪些模型可以调用。',
      '注册 embedded runtime，让系统知道怎样跑模型和工具循环。',
      '注册 WebChat、Feishu 等 channel，让消息有入口。',
      '注册内置工具，让模型后面可以按权限调用。',
    ],
    passesToNext: '产出已经装配好的 GatewayRuntime，等待 start_channels 启动通道。',
    input: '配置、环境变量、状态目录。',
    process: '加载 session，注册 provider、runtime、channel、tool。',
    output: '飞书通道和 agent runtime 准备好，等待用户发消息。',
    dataTitle: '系统能力注册表',
    dataKind: 'registries',
    dataShape: `GatewayRuntime
  provider_registry: dashscope / openai / anthropic
  runtime_registry: embedded
  channel_registry: webchat / feishu
  tool_registry: web_search / web_fetch / feishu_docs_create_with_content`,
    codeIntro: '这段代码适合按动词读：load、register、register、register。每一步都在把一种能力挂到系统里。',
    code: `self._load_sessions()  # 先恢复 session 元数据，后面消息才能接上历史
self._register_providers()  # 注册模型供应商，例如 DashScope、OpenAI、Anthropic
self._register_runtimes()  # 注册 EmbeddedRuntime，后面由它执行模型循环
self._register_channels()  # 注册消息入口，例如 webchat 和 feishu
self._register_tools()  # 注册工具能力，例如搜索、抓网页、创建飞书文档`,
    takeaway: 'boot 结束后，系统不是完成了一次任务，而是进入“能力已就绪，等待消息”的状态。',
    commonMistake: '不要把注册工具理解成执行工具。注册只是把工具放进工具箱，调用要等模型在后面提出 tool_call。',
    objectFlow: ['GatewayRuntime', 'provider_registry', 'runtime_registry', 'channel_registry', 'tool_registry'],
    questions: ['boot 注册了哪些能力？', '工具注册和工具执行有什么区别？'],
  },
  {
    id: 'start-feishu',
    phase: '飞书进线',
    title: 'start_channels 启动飞书长连接',
    short: 'start_channels',
    file: 'backend/src/watchlight/gateway/boot.py',
    fileShort: 'gateway/boot.py',
    symbol: 'GatewayRuntime.start_channels',
    studentGoal: '你要明白飞书通道是提前启动并长期等待消息的。',
    role: '它让已经注册的消息通道真正开始工作',
    story:
      '注册通道只是告诉系统“我有飞书入口”，start_channels 才是让这个入口开始监听。这里会遍历所有通道，找到启用的账号，然后调用 channel.start。对飞书长连接来说，这一步之后应用就会等飞书服务器推送消息事件。',
    exampleMoment:
      '从这一步开始，飞书用户随后发出的那句话才有可能被系统收到。',
    receivesFromPrevious: 'boot 后已经注册好的 FeishuChannelPlugin，以及配置里的飞书账号信息。',
    internalSteps: [
      '遍历 channel_registry，找出系统里有哪些通道插件。',
      '让每个通道从配置里列出启用账号。',
      '对启用账号调用 channel.start。',
      '飞书插件内部建立长连接，等待消息事件推送。',
    ],
    passesToNext: '飞书通道启动成功后，后续事件会进入 FeishuChannelPlugin.handle_event。',
    input: '已注册的 FeishuChannelPlugin 和飞书账号配置。',
    process: '遍历 channel_registry，对启用的飞书账号调用 channel.start。',
    output: '飞书长连接订阅器开始等待事件。',
    dataTitle: '飞书通道配置',
    dataKind: 'channel config',
    dataShape: `channels.feishu.accounts.default
  enabled: true
  connectionMode: websocket
  appId: FEISHU_APP_ID
  appSecret: FEISHU_APP_SECRET`,
    codeIntro: '这段代码体现了通道扩展性：Gateway 不写死飞书，而是遍历所有已注册通道。',
    code: `for channel_id in self.channel_registry.list_ids():  # 遍历系统里已经注册的通道
    channel = self.channel_registry.get(channel_id)  # 取出通道插件，可能是 webchat，也可能是 feishu
    for account_id in channel.list_account_ids(config_dict):  # 从配置里找到启用账号
        await channel.start(account_id, config_dict)  # 启动这个账号的监听能力`,
    takeaway: '飞书长连接是服务启动阶段准备好的，用户消息是运行阶段才进来的。',
    commonMistake: '不要把 start_channels 当成“发送消息”。它只是开始监听，真正的消息处理在 handle_event。',
    objectFlow: ['channel_registry', 'FeishuChannelPlugin', 'account config', 'long connection'],
    questions: ['飞书通道什么时候启动？', '这里有没有用户请求内容？'],
  },
  {
    id: 'feishu-event',
    phase: '飞书进线',
    title: '飞书用户发来创建文档请求',
    short: 'Feishu event',
    file: 'backend/src/watchlight/channels/feishu/plugin.py',
    fileShort: 'channels/feishu/plugin.py',
    symbol: 'FeishuChannelPlugin.handle_event',
    studentGoal: '你要看到外部飞书事件如何进入系统，但还没有进入模型。',
    role: '它是飞书世界和 Watchlight 世界之间的第一道适配层',
    story:
      '飞书推来的事件结构很复杂，里面有 sender、chat_id、message_id、content 等字段。Feishu 插件先做适配和过滤：是不是文本消息，是不是重复消息，是不是机器人自己发的消息，群聊里有没有 @ 当前机器人。通过这些检查后，才交给 Gateway。',
    exampleMoment:
      '用户在飞书里发出“帮我创建一个飞书文档：DeepSeek V4 的核心技术”。这句话第一次以飞书事件的形式进入项目代码。',
    receivesFromPrevious: '飞书长连接推送过来的原始消息事件。',
    internalSteps: [
      '读取飞书事件中的消息体和账号信息。',
      '调用 parse_inbound，把飞书原始结构转成 InboundMessage。',
      '过滤不支持的消息类型、自消息、重复消息和未 @ 的群消息。',
      '通过 _on_inbound 回调，把标准化消息交给 GatewayRuntime。',
    ],
    passesToNext: '把 InboundMessage 交给 GatewayRuntime._handle_inbound。',
    input: '飞书长连接收到用户消息事件。',
    process: '调用 parse_inbound，过滤重复消息、自消息、未 @ 的群消息。',
    output: '标准化后的 InboundMessage。',
    dataTitle: '用户输入示例',
    dataKind: 'Feishu text event',
    dataShape: `用户在飞书发送：
"帮我创建一个飞书文档：DeepSeek V4 的核心技术"

飞书事件里包含：
- sender.open_id
- message.chat_id
- message.message_id
- content.text`,
    codeIntro: '这段代码要看两件事：先 parse，再过滤。过滤通过后才进入统一 Gateway 主线。',
    code: `msg = parse_inbound({**event_data, "account_id": account_id})  # 把飞书原始事件翻译成内部消息
if msg is None:  # 如果不是系统支持的文本消息
    return False  # 本条事件不进入 agent
if message_id and self._is_duplicate_message(message_id):  # 飞书可能重投同一条消息
    return False  # 防止重复创建文档和重复回复
await self._on_inbound(msg)  # 交给 GatewayRuntime._handle_inbound，进入统一处理入口`,
    takeaway: '飞书插件只负责适配和过滤，不负责调模型，也不负责创建文档。',
    commonMistake: '看到 FeishuChannelPlugin 不要以为文档就在这里创建。它只是把飞书消息变成系统能理解的消息。',
    objectFlow: ['Feishu event', 'parse_inbound', 'InboundMessage', '_on_inbound'],
    questions: ['飞书原始事件在哪里转成 InboundMessage？', '为什么要去重？'],
  },
  {
    id: 'parse-inbound',
    phase: '飞书进线',
    title: 'message.py 生成 InboundMessage',
    short: 'InboundMessage',
    file: 'backend/src/watchlight/channels/feishu/message.py',
    fileShort: 'channels/feishu/message.py',
    symbol: 'parse_inbound',
    studentGoal: '你要理解统一消息格式的价值：后面的主线不用认识飞书原始字段。',
    role: '它把飞书方言翻译成 Watchlight 普通话',
    story:
      '不同平台的消息结构都不一样。飞书有自己的 sender、chat_id、message_id、content 格式，WebChat 或别的通道又不同。parse_inbound 的任务就是把这些差异压平，统一成 channel、senderId、conversationId、text 这些字段。',
    exampleMoment:
      '“帮我创建文档”这句话在这里从飞书 content JSON 里被取出来，变成 InboundMessage.text。',
    receivesFromPrevious: 'FeishuChannelPlugin 传入的 event_data。',
    internalSteps: [
      '从 content JSON 里取出用户文本。',
      '读取 sender_id，用来区分是谁发的。',
      '读取 chat_id，用来确定这条消息属于哪个会话。',
      '记录群聊是否 @ 机器人。',
      '清理 @ 标签，返回 InboundMessage。',
    ],
    passesToNext: '产出统一 InboundMessage，交给 GatewayRuntime._handle_inbound。',
    input: '飞书 event_data。',
    process: '读取 sender_id、chat_id、message_id、text，并移除 @ 标签。',
    output: 'Watchlight 内部统一的 InboundMessage。',
    dataTitle: '标准化后的消息',
    dataKind: 'InboundMessage',
    dataShape: `InboundMessage(
  channel="feishu",
  accountId="default",
  senderId="ou_xxx",
  conversationId="oc_xxx",
  text="帮我创建一个飞书文档：DeepSeek V4 的核心技术",
  chatType="dm",
  raw={...}
)`,
    codeIntro: '这段代码适合逐字段读：text 是用户说的话，senderId 是谁说的，conversationId 是在哪个会话里说的。',
    code: `text = _read_text(event_data.get("content", message.get("content", "{}")))  # 从飞书 content JSON 中取出文本
sender_id = _read_sender_id(sender)  # 读取发送者 open_id，后面用来区分用户
chat_id = event_data.get("chat_id", message.get("chat_id", ""))  # 读取会话 id，后面用来定位 session
raw["mentioned_bot"] = _mentioned_bot(message, text)  # 记录群聊里是否 @ 当前机器人
return InboundMessage(channel="feishu", senderId=str(sender_id or ""), conversationId=str(chat_id or ""), text=_AT_TAG_RE.sub("", text).strip(), raw=raw)  # 返回统一入站消息`,
    takeaway: 'InboundMessage 是所有通道进入 agent 主线前的统一格式。',
    commonMistake: '不要把 raw 当成主线数据。raw 保留原始事件用于排查，主线主要看 channel、senderId、conversationId 和 text。',
    objectFlow: ['Feishu content JSON', 'text', 'senderId', 'conversationId', 'InboundMessage'],
    questions: ['为什么要移除 @ 标签？', 'conversationId 后面用来做什么？'],
  },
  {
    id: 'handle-inbound',
    phase: '飞书进线',
    title: '_handle_inbound 进入 Gateway 统一入口',
    short: '_handle_inbound',
    file: 'backend/src/watchlight/gateway/boot.py',
    fileShort: 'gateway/boot.py',
    symbol: 'GatewayRuntime._handle_inbound',
    studentGoal: '你要看到飞书、WebChat 等入口最终都会汇合到 GatewayRuntime。',
    role: '它是所有消息通道进入 agent 主线的汇合口',
    story:
      '到这里，系统已经不太关心消息来自飞书还是别的平台了。_handle_inbound 会先算 session_key，确定这条消息属于哪个会话，再发 runtime event 给前端观察，然后调用 run_agent_for_session 进入真正 agent 主线。',
    exampleMoment:
      '飞书用户的这句话在这里被绑定到一个 session，比如 feishu:oc_xxx:ou_xxx。之后历史消息、模型输出、工具结果都归到这个 session。',
    receivesFromPrevious: '标准化后的 InboundMessage。',
    internalSteps: [
      '根据 channel、conversationId、senderId 计算 session_key。',
      '广播 runtime.channel.inbound，让前端知道有消息进来了。',
      '把用户文本、通道、账号等信息传给 run_agent_for_session。',
      '等待 agent 执行完成，再准备回通道回复。',
    ],
    passesToNext: '调用 GatewayRuntime.run_agent_for_session，进入模型和工具执行准备阶段。',
    input: '标准化后的 InboundMessage。',
    process: '计算 session_key，记录入站事件，然后调用 run_agent_for_session。',
    output: '进入统一 agent 执行函数。',
    dataTitle: 'session 路由',
    dataKind: 'session key',
    dataShape: `输入：
channel = "feishu"
senderId = "ou_xxx"
conversationId = "oc_xxx"

输出：
session_key = "feishu:oc_xxx:ou_xxx"`,
    codeIntro: '这段代码是通道层到 agent 层的门。重点看 session_key 和 run_agent_for_session。',
    code: `session_key = resolve_session_key(message)  # 计算内部会话 key，后面读写历史都靠它
await self._emit_runtime_event("runtime.channel.inbound", ...)  # 广播入站事件，前端可以实时显示
result = await self.run_agent_for_session(  # 进入统一 agent 执行函数
  session_key=session_key,  # 告诉 agent 本次运行属于哪个会话
  user_message=message.text or "",  # 把飞书文本作为用户输入
  channel=message.channel,  # 保留来源通道，后面决定工具策略和回包方式
)  # 等待模型和工具链路完成`,
    takeaway: '飞书入口在这里变成统一 agent 请求，不再走飞书专属业务分支。',
    commonMistake: 'runtime event 不是业务执行本身，它是给前端观察运行过程用的事件流。',
    objectFlow: ['InboundMessage', 'session_key', 'runtime.channel.inbound', 'run_agent_for_session'],
    questions: ['session_key 为什么要包含通道和会话？', 'runtime.channel.inbound 是给谁看的？'],
  },
  {
    id: 'run-agent',
    phase: 'Agent 执行',
    title: 'run_agent_for_session 读取历史并组装任务',
    short: 'run_agent_for_session',
    file: 'backend/src/watchlight/gateway/boot.py',
    fileShort: 'gateway/boot.py',
    symbol: 'GatewayRuntime.run_agent_for_session',
    studentGoal: '你要看懂模型执行前的准备：历史、system prompt、工具说明、工具策略。',
    role: '它把一条用户消息整理成模型 runtime 能执行的任务单',
    story:
      '模型不能只收到一句孤零零的用户消息。它还需要 system prompt、历史对话、允许使用的工具说明、模型供应商和模型 id。run_agent_for_session 就是在整理这些材料，然后打包成 AgentRunRequest。',
    exampleMoment:
      '“帮我创建文档”会被写入 transcript，历史上下文会一起带给模型。因为消息来自飞书，toolProfile 会使用 messaging，避免远程聊天入口直接获得危险本地工具。',
    receivesFromPrevious: 'session_key、用户文本、channel、account_id、reply_to 等通道上下文。',
    internalSteps: [
      '用 session_key 找到或创建 session。',
      '读取 transcript，把历史消息取出来。',
      '把当前用户消息写入 transcript。',
      '根据通道选择 toolProfile。',
      '组装 system prompt、history、user_message 和 metadata。',
      '创建 AgentRunRequest，交给 runtime.run。',
    ],
    passesToNext: '把 AgentRunRequest 交给 EmbeddedRuntime.run。',
    input: 'session_key 和用户请求文本。',
    process: '读取 transcript，把本轮 user 写入 transcript，构造 system prompt、history、toolProfile。',
    output: 'AgentRunRequest，交给 runtime.run。',
    dataTitle: '本轮模型任务',
    dataKind: 'AgentRunRequest',
    dataShape: `AgentRunRequest(
  provider_id="dashscope",
  model_id="qwen3.6-max-preview",
  user_message="帮我创建一个飞书文档：DeepSeek V4 的核心技术",
  history=[...],
  metadata={
    "channel": "feishu",
    "toolProfile": "messaging"
  }
)`,
    codeIntro: '这段代码是“准备模型输入”。注意 history、system_prompt、toolProfile 是在这里合流的。',
    code: `raw = self.transcript_manager.read_raw(entry.session_id)  # 读取这个会话过去的消息
history = [h for h in raw if h.get("role") in ("user", "assistant", "system")]  # 只保留模型能理解的角色
self.transcript_manager.append(entry.session_id, {"role": "user", "content": user_message, "ts": int(time.time() * 1000)})  # 把本轮飞书消息写入历史
tool_profile = "messaging" if channel else "full"  # 飞书入口使用更保守的工具策略
effective_system_prompt = build_system_prompt(identity=system_prompt, tool_instructions=_tool_prompt_instructions(self.tool_registry, tool_profile))  # 合并身份提示词和工具说明
request = AgentRunRequest(run_id=run_id, session_key=session_key, provider_id=self.default_provider, model_id=self.default_model, system_prompt=effective_system_prompt, user_message=user_message, history=history, metadata={"channel": channel, "toolProfile": tool_profile})  # 创建 runtime 任务单`,
    takeaway: 'Gateway 不直接调模型，它先把一次运行需要的上下文整理成 AgentRunRequest。',
    commonMistake: '不要把 transcript 和模型上下文混为一谈。transcript 是本地存档，history 是从存档里筛出来给模型看的上下文。',
    objectFlow: ['session_key', 'transcript', 'system prompt', 'toolProfile', 'AgentRunRequest'],
    questions: ['history 从哪里来？', 'toolProfile 为什么飞书用 messaging？'],
  },
  {
    id: 'runner',
    phase: 'Agent 执行',
    title: 'runner.py 调模型并识别工具调用',
    short: 'runner.py',
    file: 'backend/src/watchlight/agents/runtime/embedded/runner.py',
    fileShort: 'runtime/embedded/runner.py',
    symbol: 'EmbeddedRuntime._single_attempt',
    studentGoal: '你要看懂模型并不是直接创建文档，而是先判断要不要调用工具。',
    role: '它是真正驱动模型流式输出和工具意图识别的执行引擎',
    story:
      '到 runner.py 时，飞书已经退到背景里了。这里面对的是标准模型任务：messages、system prompt、tool definitions。模型可能先输出一点思考性文本，也可能直接提出 tool_call，比如先 web_search 查 DeepSeek V4，再 web_fetch 抓资料，最后调用飞书文档工具。',
    exampleMoment:
      '如果模型判断“DeepSeek V4 的核心技术”需要新资料，它应该先调 web_search 和 web_fetch；如果要交付文档，它应该调用 feishu_docs_create_with_content，而不是把整篇正文发在聊天里。',
    receivesFromPrevious: 'GatewayRuntime 创建的 AgentRunRequest，以及 provider_registry、tool_registry。',
    internalSteps: [
      '根据 toolProfile 生成工具策略，只暴露允许的工具。',
      '把 system、history、user_message 组装成模型 messages。',
      '调用 provider.create_stream，开始接收模型流。',
      '遇到 text_delta 就产出文本事件。',
      '遇到 tool_call 就收集起来，准备交给工具循环执行。',
    ],
    passesToNext: '把模型提出的 tool_call 交给 tool_loop.py 执行。',
    input: 'AgentRunRequest、provider_registry、tool_registry。',
    process: '按 toolProfile 过滤工具，调用 provider.create_stream，收集 text_delta 和 tool_call。',
    output: 'AgentEvent 流，包含文本、工具调用开始、工具结果等。',
    dataTitle: '模型可能提出的工具计划',
    dataKind: 'tool calls',
    dataShape: `可能的工具调用：
1. web_search({"query": "DeepSeek V4 core technology paper"})
2. web_fetch({"url": "..."})
3. feishu_docs_create_with_content({
     "title": "DeepSeek V4 的核心技术",
     "content": "..."
   })`,
    codeIntro: '这段代码说明工具不是硬编码分支，而是作为 tool_defs 暴露给模型，由模型产生 tool_call。',
    code: `tool_defs = [tool for tool in self._tool_registry.catalog() if tool_policy.is_allowed(str(tool.get("name", "")))]  # 根据策略筛出本次允许给模型看的工具
async for chunk in provider.create_stream(model=request.model_id, messages=messages, system=request.system_prompt, tools=tool_defs):  # 调模型供应商的流式接口
    if chunk.get("type") == "text_delta":  # 模型返回普通文本片段
        yield AgentEvent(type=AgentEventType.TEXT_DELTA, text=chunk.get("text", ""))  # 把文本片段转成 runtime 事件
    elif chunk.get("type") == "tool_call":  # 模型提出工具调用意图
        tool_calls.append(chunk)  # 先收集，之后交给 tool_loop 统一执行`,
    takeaway: 'runner.py 负责让模型“看见工具并提出调用”，但不直接执行工具。',
    commonMistake: '模型返回 tool_call 不等于工具已经执行。tool_call 只是意图，真实执行要等 tool_loop。',
    objectFlow: ['AgentRunRequest', 'messages', 'tool_defs', 'provider stream', 'tool_call'],
    questions: ['工具列表在哪里传给模型？', '模型返回 tool_call 后谁执行？'],
  },
  {
    id: 'tool-loop',
    phase: '工具调用',
    title: 'tool_loop.py 执行搜索和飞书文档工具',
    short: 'tool_loop.py',
    file: 'backend/src/watchlight/agents/runtime/embedded/tool_loop.py',
    fileShort: 'runtime/embedded/tool_loop.py',
    symbol: 'run_tool_loop',
    studentGoal: '你要理解模型负责提出意图，系统负责检查权限并执行工具。',
    role: '它是模型意图进入真实工具世界的执行关口',
    story:
      'tool_loop 的角色很关键：模型说“我要调用 web_search”，系统不能盲目执行。它要先检查工具是否存在、是否被当前策略允许，然后才调用 execute_tool。执行结果会变成 role=tool 的消息，再送回模型，让模型基于结果继续下一步。',
    exampleMoment:
      '这条文档请求可能会连续经过 web_search、web_fetch、feishu_docs_create_with_content。每个工具结果都会被记录成事件，前端运行工作台也能看到。',
    receivesFromPrevious: 'runner.py 收集到的 tool_calls、tool_registry、tool_policy 和 ToolContext。',
    internalSteps: [
      '为每个工具调用产出 TOOL_CALL_START 事件。',
      '通过 execute_tool 检查权限并执行真实工具。',
      '把工具输出序列化成字符串。',
      '产出 TOOL_CALL_RESULT 事件，方便前端观察。',
      '把结果包装成 role=tool 消息，追加回模型 messages。',
    ],
    passesToNext: '把 tool_results 追加回 messages，交给 runner 发起下一轮模型调用。',
    input: 'tool_calls、tool_registry、tool_policy、ToolContext。',
    process: '逐个检查并执行工具，把结果包装成 role=tool 消息。',
    output: 'tool_results 被追加回 messages，模型可继续生成最终答案。',
    dataTitle: '工具结果如何回到模型',
    dataKind: 'role=tool messages',
    dataShape: `messages += [
  {
    "role": "tool",
    "name": "web_search",
    "content": "{搜索结果...}"
  },
  {
    "role": "tool",
    "name": "feishu_docs_create_with_content",
    "content": "{document_id, url, reply_text}"
  }
]`,
    codeIntro: '这段代码把工具调用拆成可观察的事件和可继续喂给模型的 tool 消息。',
    code: `events.append(AgentEvent(type=AgentEventType.TOOL_CALL_START, tool_name=tool_name, tool_params=tool_params))  # 告诉前端：某个工具要开始执行了
result = await execute_tool(tool_registry, tool_policy, tool_name, tool_params, context)  # 检查权限并执行真实工具
output_str = json.dumps(result.output, ensure_ascii=False, default=str) if result.success else f"Error: {result.error}"  # 把工具结果转成模型可读文本
events.append(AgentEvent(type=AgentEventType.TOOL_CALL_RESULT, tool_name=tool_name, tool_result=output_str))  # 告诉前端：工具执行完成并返回结果
tool_results.append({"role": "tool", "tool_call_id": tool_id, "name": tool_name, "content": output_str})  # 把结果变成下一轮模型消息`,
    takeaway: '工具调用是模型意图和真实系统能力之间的边界。',
    commonMistake: '不要让模型直接“拥有”工具执行权。系统必须用 tool_policy 和 execute_tool 做统一边界。',
    objectFlow: ['tool_call', 'tool_policy', 'execute_tool', 'TOOL_CALL_RESULT', 'role=tool'],
    questions: ['execute_tool 之前为什么要有 tool_policy？', '工具结果为什么要写成 role=tool？'],
  },
  {
    id: 'feishu-doc-tool',
    phase: '工具调用',
    title: 'feishu_docs_create_with_content 创建文档',
    short: 'feishu_docs',
    file: 'backend/src/watchlight/tools/builtin/feishu_docs.py',
    fileShort: 'tools/builtin/feishu_docs.py',
    symbol: 'feishu_docs_create_with_content',
    studentGoal: '你要确认创建飞书文档是一个工具，不是写死在 prompt 或 if 判断里的特殊逻辑。',
    role: '它把模型整理好的内容落到飞书云文档里',
    story:
      '这个工具才是真正接触飞书文档 OpenAPI 的地方。模型传入标题和正文，工具负责创建文档、转换正文 block、写入内容、生成链接。这样以后要加表格、评论、权限等能力，也可以继续扩展工具，而不是把业务塞进 runner。',
    exampleMoment:
      '模型传来的 title 应该是“DeepSeek V4 的核心技术”，content 是整理好的文章正文。工具执行成功后，聊天里只需要回复文档链接，正文留在文档里。',
    receivesFromPrevious: 'tool_loop 执行工具时传入的 params、ToolContext 和飞书配置。',
    internalSteps: [
      '读取模型传来的 title 和 content。',
      '获取飞书 app token，准备调用飞书文档 API。',
      '创建新版文档，拿到 document_id。',
      '把正文转换成飞书文档 blocks。',
      '写入文档内容，生成 url 和 reply_text。',
    ],
    passesToNext: '把 document_id、url、reply_text 作为工具结果返回给 tool_loop。',
    input: '模型整理好的标题和正文内容。',
    process: '调用飞书文档 OpenAPI 创建文档、写入正文、生成可回复链接。',
    output: '工具结果包含 document_id、url、reply_text。',
    dataTitle: '飞书文档工具结果',
    dataKind: 'tool result',
    dataShape: `{
  "document_id": "docx_xxx",
  "url": "https://xxx.feishu.cn/docx/xxx",
  "reply_text": "已创建飞书文档：DeepSeek V4 的核心技术\\nhttps://xxx.feishu.cn/docx/xxx"
}`,
    codeIntro: '这段代码是工具的核心路径：拿参数、调飞书、写 block、返回链接。',
    code: `title = str(params.get("title") or "").strip()  # 读取模型给出的文档标题
content = str(params.get("content") or "").strip()  # 读取模型整理好的文档正文
document = await docs.create_document(title=title, folder_token=folder_token)  # 调飞书 API 创建新版文档
await docs.replace_document_blocks(document_id, blocks)  # 把正文转换成飞书 blocks 后写入文档
return json.dumps({"document_id": document_id, "url": url, "reply_text": reply_text}, ensure_ascii=False)  # 返回工具结果，尤其是可直接回复用户的链接文本`,
    takeaway: '创建文档是标准工具调用结果，不应该在聊天窗口输出整篇文档正文。',
    commonMistake: '不要把“模型生成正文”和“飞书写文档”混在一个模块里。模型负责内容，工具负责落地到飞书。',
    objectFlow: ['tool params', 'Feishu Docs API', 'document blocks', 'document url', 'reply_text'],
    questions: ['为什么工具要返回 reply_text？', '文档正文应该出现在飞书文档还是聊天窗口？'],
  },
  {
    id: 'reply',
    phase: '回复',
    title: 'Gateway 写 assistant transcript 并回复飞书',
    short: 'reply',
    file: 'backend/src/watchlight/gateway/boot.py',
    fileShort: 'gateway/boot.py',
    symbol: 'runtime.run completed + channel.send',
    studentGoal: '你要看到系统如何从 runtime 结果回到飞书用户。',
    role: '它负责收尾：保存结果，选择最终回复，发回原通道',
    story:
      '一次 agent 运行结束后，Gateway 要做三件事：确定最终要发什么，写入 assistant transcript，调用通道 send 发回用户。对于创建文档场景，最理想的最终回复不是长文正文，而是“已创建文档 + 链接”。',
    exampleMoment:
      '飞书用户最终应该收到类似“已创建飞书文档：DeepSeek V4 的核心技术 + 链接”。如果模型还生成了正文，那正文也不应该刷在聊天里。',
    receivesFromPrevious: 'runtime.run 返回的 AgentRunResult，以及通道上下文中的 conversation_id、reply_to。',
    internalSteps: [
      '从工具结果里提取 reply_text。',
      '如果有文档链接回复，就优先使用它作为最终 response。',
      '把 assistant 回复写入 transcript。',
      '构造 OutboundMessage。',
      '调用飞书 channel_plugin.send，把消息发回原会话。',
    ],
    passesToNext: '通过 FeishuChannelPlugin.send 调用飞书发送消息 API，用户在飞书里看到结果。',
    input: 'runtime.run 结束后的 AgentRunResult。',
    process: '如果工具结果包含 reply_text，用它覆盖长正文；写 assistant transcript；调用飞书通道 send。',
    output: '飞书用户收到文档链接。',
    dataTitle: '最终飞书回复',
    dataKind: 'OutboundMessage',
    dataShape: `OutboundMessage(
  text="已创建飞书文档：DeepSeek V4 的核心技术\\nhttps://xxx.feishu.cn/docx/xxx",
  replyToId="om_xxx"
)`,
    codeIntro: '这段代码是回包链路。重点看 preferred_response 如何把文档工具链接变成最终聊天回复。',
    code: `reply_text = _extract_tool_reply_text(event.tool_result)  # 从工具结果里提取适合直接发给用户的链接回复
if reply_text:  # 如果文档工具返回了 reply_text
    result.preferred_response = reply_text  # 用链接回复覆盖模型可能生成的长正文
response_text = result.preferred_response or "".join(result.texts) or "[No response]"  # 得到最终要发给用户的文本
self.transcript_manager.append(entry.session_id, {"role": "assistant", "content": response_text, "ts": int(time.time() * 1000)})  # 保存 assistant 回复
outbound = OutboundMessage(text=response_text, replyToId=reply_to)  # 构造通道出站消息
await channel_plugin.send(account_id, message.conversation_id, outbound)  # 调飞书通道，把回复发回原会话`,
    takeaway: '最后回到 Gateway 收尾：保存历史，发 runtime.event，回飞书通道。',
    commonMistake: '最终回复不应该重新生成一篇文档正文。创建文档成功时，聊天窗口只需要给用户可点击链接。',
    objectFlow: ['AgentRunResult', 'preferred_response', 'assistant transcript', 'OutboundMessage', 'Feishu send'],
    questions: ['为什么创建文档后只回复链接？', 'channel_plugin.send 最终会走到哪个飞书 API？'],
  },
]

const activeIndex = ref(0)
const activeModule = computed(() => modules[activeIndex.value])
</script>

<style scoped>
:global(*) {
  box-sizing: border-box;
}
:global(html),
:global(body),
:global(#walkthrough) {
  height: 100%;
  overflow: hidden;
}
:global(body) {
  margin: 0;
  background: #f4f5f7;
  color: #1a1d21;
  font-family: 'Inter Tight', 'Noto Sans SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
:global(button) {
  font-family: inherit;
}
.walk-shell {
  --bg: #f4f5f7;
  --text: #1a1d21;
  --accent: #0055ff;
  --border: #d1d5db;
  --muted: rgba(26, 29, 33, 0.62);
  --green: #16a34a;
  --mono: 'JetBrains Mono', 'SFMono-Regular', Consolas, monospace;
  height: 100dvh;
  overflow: hidden;
  background: var(--bg);
}
.grid-bg {
  position: fixed;
  inset: 0;
  pointer-events: none;
  opacity: 0.22;
  background-size: 60px 60px;
  background-image:
    linear-gradient(to right, #d1d5db 1px, transparent 1px),
    linear-gradient(to bottom, #d1d5db 1px, transparent 1px);
  mask-image: linear-gradient(to bottom, black 35%, transparent 100%);
}
.topbar {
  position: relative;
  z-index: 2;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 0 24px;
  border-bottom: 1px solid var(--border);
  background: rgba(244, 245, 247, 0.92);
  backdrop-filter: blur(14px);
}
.brand {
  display: flex;
  align-items: center;
  gap: 13px;
}
.brand-mark {
  width: 18px;
  height: 18px;
  background: var(--accent);
  box-shadow: 7px 7px 0 #1a1d21;
}
.eyebrow {
  margin: 0 0 6px;
  color: var(--accent);
  font: 800 10px/1 var(--mono);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
h1,
h2,
h3,
p {
  margin: 0;
}
h1 {
  font-size: 22px;
  line-height: 1.1;
}
.top-tags {
  display: flex;
  border: 1px solid var(--border);
  background: var(--border);
  gap: 1px;
}
.top-tags span {
  white-space: nowrap;
  background: #fff;
  padding: 10px 12px;
  color: var(--muted);
  font: 700 10px/1 var(--mono);
}
.scenario {
  position: relative;
  z-index: 1;
  height: 126px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(340px, 38%);
  gap: 24px;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border);
  background: #fff;
}
.scenario h2 {
  font-size: clamp(24px, 3vw, 40px);
  line-height: 1.06;
  font-weight: 650;
}
.scenario p:not(.eyebrow) {
  color: rgba(26, 29, 33, 0.72);
  font-size: 14px;
  line-height: 1.65;
}
.top-flow {
  position: relative;
  z-index: 1;
  height: 132px;
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(156px, 1fr);
  gap: 1px;
  overflow-x: auto;
  background: var(--border);
  border-bottom: 1px solid var(--border);
}
.flow-step {
  position: relative;
  border: 0;
  background: #fff;
  color: var(--text);
  text-align: left;
  padding: 14px;
  cursor: pointer;
}
.flow-step:not(:last-child)::after {
  content: "";
  position: absolute;
  right: -8px;
  top: 50%;
  width: 16px;
  height: 16px;
  border-top: 1px solid var(--border);
  border-right: 1px solid var(--border);
  background: inherit;
  transform: translateY(-50%) rotate(45deg);
  z-index: 2;
}
.flow-step:hover {
  background: #f8fbff;
}
.flow-step.done {
  box-shadow: inset 0 4px 0 var(--green);
}
.flow-step.active {
  background: #eef4ff;
  box-shadow: inset 0 4px 0 var(--accent);
}
.step-no {
  display: inline-grid;
  place-items: center;
  width: 28px;
  height: 24px;
  border: 1px solid var(--border);
  background: #fff;
  color: var(--accent);
  font: 800 11px/1 var(--mono);
}
.flow-step strong,
.flow-step small {
  display: block;
}
.flow-step strong {
  margin-top: 13px;
  font-size: 14px;
  line-height: 1.2;
}
.flow-step small {
  margin-top: 8px;
  color: var(--muted);
  font: 700 10px/1.3 var(--mono);
}
.workspace {
  position: relative;
  z-index: 1;
  height: calc(100dvh - 72px - 126px - 132px);
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr) 340px;
  overflow: hidden;
}
.module-list,
.detail,
.right-panel {
  min-height: 0;
  overflow: hidden;
}
.module-list {
  border-right: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.78);
}
.list-head {
  padding: 16px 18px;
  border-bottom: 1px solid var(--border);
}
.list-head strong {
  font-size: 15px;
}
.module-tab {
  width: 100%;
  min-height: 86px;
  display: block;
  border: 0;
  border-bottom: 1px solid var(--border);
  background: transparent;
  color: var(--text);
  text-align: left;
  padding: 13px 18px;
  cursor: pointer;
}
.module-tab:hover {
  background: rgba(0, 85, 255, 0.06);
}
.module-tab.active {
  background: #fff;
  box-shadow: inset 4px 0 0 var(--accent);
}
.module-tab span,
.module-tab strong,
.module-tab small {
  display: block;
}
.module-tab span {
  color: var(--accent);
  font: 800 10px/1 var(--mono);
}
.module-tab strong {
  margin-top: 8px;
  font-size: 14px;
}
.module-tab small {
  margin-top: 7px;
  color: var(--muted);
  font: 700 10px/1.3 var(--mono);
}
.detail {
  background:
    linear-gradient(to right, rgba(209, 213, 219, 0.32) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(209, 213, 219, 0.32) 1px, transparent 1px);
  background-size: 36px 36px;
}
.detail-scroll,
.right-scroll {
  height: 100%;
  overflow: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
}
.module-hero,
.story-board,
.handoff-board,
.steps-board,
.io-board,
.data-board,
.code-board {
  margin: 22px;
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.96);
}
.module-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 36%);
  gap: 24px;
  align-items: end;
  padding: 22px;
}
.module-hero h2 {
  font-size: clamp(28px, 3.4vw, 48px);
  line-height: 1.02;
  font-weight: 650;
}
.module-hero p:not(.eyebrow) {
  margin-top: 14px;
  color: rgba(26, 29, 33, 0.74);
  font-size: 16px;
  line-height: 1.65;
}
.position-box {
  border: 1px solid var(--border);
  background: #f9fafb;
  padding: 16px;
}
.position-box span,
.handoff-board span,
.io-board span {
  display: block;
  color: var(--accent);
  font: 800 10px/1 var(--mono);
  text-transform: uppercase;
}
.position-box strong,
.position-box em {
  display: block;
}
.position-box strong {
  margin-top: 12px;
  font: 700 12px/1.4 var(--mono);
  color: #111827;
}
.position-box em {
  margin-top: 10px;
  color: var(--muted);
  font-style: normal;
  font: 700 11px/1.3 var(--mono);
}
.story-board {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(260px, 34%);
  gap: 1px;
  background: var(--border);
}
.story-main,
.story-side {
  background: #fff;
  padding: 20px;
}
.story-main h3 {
  font-size: 24px;
  line-height: 1.18;
}
.story-main p:not(.eyebrow),
.story-side p:not(.eyebrow) {
  margin-top: 13px;
  color: rgba(26, 29, 33, 0.76);
  font-size: 15px;
  line-height: 1.76;
}
.story-side {
  background: #f8fbff;
}
.handoff-board,
.io-board {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1px;
  background: var(--border);
}
.io-board {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.handoff-board article,
.io-board article {
  min-height: 126px;
  padding: 18px;
  background: #fff;
}
.handoff-board p,
.io-board p {
  margin-top: 15px;
  color: rgba(26, 29, 33, 0.76);
  font-size: 14px;
  line-height: 1.65;
}
.section-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding: 18px;
  border-bottom: 1px solid var(--border);
}
.section-head h3 {
  font-size: 17px;
  line-height: 1.1;
}
.section-head code {
  color: var(--muted);
  font: 700 11px/1.2 var(--mono);
}
.steps-board ol {
  margin: 0;
  padding: 8px 18px 18px;
  list-style: none;
  counter-reset: steps;
}
.steps-board li {
  counter-increment: steps;
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr);
  gap: 13px;
  padding: 14px 0;
  border-top: 1px solid rgba(209, 213, 219, 0.82);
  color: rgba(26, 29, 33, 0.78);
  font-size: 15px;
  line-height: 1.6;
}
.steps-board li::before {
  content: counter(steps, decimal-leading-zero);
  color: var(--accent);
  font: 800 11px/1.6 var(--mono);
}
pre {
  margin: 0;
  padding: 18px;
  overflow: auto;
}
code {
  font-family: var(--mono);
}
pre code {
  font-size: 12px;
  line-height: 1.65;
}
.data-board pre code {
  color: #1a1d21;
}
.code-board {
  background: #101317;
  color: #e5e7eb;
}
.dark-head {
  border-bottom-color: rgba(255, 255, 255, 0.12);
}
.dark-head h3,
.dark-head code {
  color: #fff;
}
.code-intro {
  padding: 16px 18px 0;
  color: rgba(255, 255, 255, 0.78);
  font-size: 14px;
  line-height: 1.7;
}
.code-board pre code {
  color: #e5e7eb;
}
.right-panel {
  border-left: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.78);
}
.checkpoint {
  padding: 18px;
  border-bottom: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.88);
}
.checkpoint h3 {
  font-size: 20px;
  line-height: 1.35;
}
.checkpoint p:not(.eyebrow) {
  color: rgba(26, 29, 33, 0.76);
  font-size: 14px;
  line-height: 1.68;
}
.checkpoint ul {
  margin: 14px 0 0;
  padding: 0;
  list-style: none;
}
.checkpoint li {
  position: relative;
  padding: 11px 0 11px 18px;
  border-top: 1px solid rgba(209, 213, 219, 0.82);
  color: rgba(26, 29, 33, 0.78);
  font-size: 14px;
  line-height: 1.55;
}
.checkpoint li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 19px;
  width: 7px;
  height: 7px;
  background: var(--accent);
}
.object-flow li {
  font-family: var(--mono);
  font-size: 12px;
}
.checkpoint.dark {
  background: #1a1d21;
  color: #fff;
}
.checkpoint.dark p:not(.eyebrow) {
  margin-top: 12px;
  color: rgba(255, 255, 255, 0.82);
  font-size: 14px;
  line-height: 1.7;
}
:global(::-webkit-scrollbar) {
  width: 7px;
  height: 7px;
}
:global(::-webkit-scrollbar-track) {
  background: #f4f5f7;
}
:global(::-webkit-scrollbar-thumb) {
  background: #c4cad3;
}
@media (max-width: 1180px) {
  .workspace {
    grid-template-columns: 270px minmax(0, 1fr);
  }
  .right-panel {
    display: none;
  }
}
@media (max-width: 900px) {
  :global(html),
  :global(body),
  :global(#walkthrough) {
    overflow: auto;
  }
  .walk-shell {
    height: auto;
    min-height: 100dvh;
    overflow: visible;
  }
  .topbar,
  .scenario,
  .module-hero,
  .story-board,
  .handoff-board,
  .io-board {
    display: block;
    height: auto;
  }
  .workspace {
    height: auto;
    display: block;
    overflow: visible;
  }
  .module-list,
  .detail,
  .right-panel,
  .detail-scroll,
  .right-scroll {
    height: auto;
    overflow: visible;
  }
}
</style>
