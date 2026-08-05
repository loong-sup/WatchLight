# Watchlight 主工作台视觉与观测体验升级 Tasks

> 输入：已批准的 `spec.md` 与 `plan.md`

## 文件清单

| 操作 | 文件 | 职责 |
|---|---|---|
| 修改 | `frontend/src/App.vue` | 顶栏、指标、设计变量、布局与检查器开关 |
| 修改 | `frontend/src/components/RunList.vue` | 会话导航 |
| 修改 | `frontend/src/components/ArchitectureMap.vue` | 架构光迹 |
| 修改 | `frontend/src/components/RuntimeTimeline.vue` | 运行内容与事件时间线 |
| 修改 | `frontend/src/components/InspectorPanel.vue` | 输出检查器 |
| 修改 | `frontend/src/components/ToolCallPanel.vue` | 工具结果 |
| 修改 | `frontend/src/components/MessageContextPanel.vue` | 消息上下文 |
| 修改 | `frontend/src/components/Composer.vue` | 消息输入 |

## T1：建立全局视觉系统与主框架

**文件：** `frontend/src/App.vue`  
**依赖：** 无  
**步骤：** 建立颜色、间距、圆角、阴影与焦点变量；重构品牌顶栏；派生并展示基础指标；加入检查器显隐；调整三栏响应式布局。  
**验证：** 运行前端构建，模板与类型检查通过。

## T2：升级会话导航

**文件：** `frontend/src/components/RunList.vue`  
**依赖：** T1  
**步骤：** 重构头部和摘要；增加状态图标与更清晰的选中态；处理长文本与空状态；补充键盘焦点。  
**验证：** 页面中会话列表可刷新、可切换，长标题不撑破布局。

## T3：实现品牌光迹

**文件：** `frontend/src/components/ArchitectureMap.vue`  
**依赖：** T1  
**步骤：** 重构节点布局；建立连续轨道；为活动、完成、失败、等待状态加入形态和文字差异；添加低干扰光迹动画及减少动态效果规则。  
**验证：** 七个节点均显示，状态切换不改变数据行为，减少动态效果下无持续动画。

## T4：重构运行时间线层级

**文件：** `frontend/src/components/RuntimeTimeline.vue`  
**依赖：** T1、T3  
**步骤：** 加入运行摘要；区分输入、工具、模型输出和回写；重做事件轨道；统一空状态和溢出处理。  
**验证：** 有运行和无运行两种状态均正常渲染，链接和长文本可访问。

## T5：升级检查器内容

**文件：** `InspectorPanel.vue`、`ToolCallPanel.vue`、`MessageContextPanel.vue`  
**依赖：** T1  
**步骤：** 统一分区标题、数量标签、状态卡片、代码块和折叠控件；改善最终回复的阅读层级。  
**验证：** 输出、工具结果、参数和两种上下文标签均可访问。

## T6：升级消息输入区

**文件：** `frontend/src/components/Composer.vue`  
**依赖：** T1  
**步骤：** 重构输入容器、状态反馈、按钮与快捷提示；保持发送逻辑不变。  
**验证：** 空输入不可发送，输入后可发送，发送状态可见。

## T7：构建与视觉验收

**文件：** 上述全部文件  
**依赖：** T1 至 T6  
**步骤：** 执行生产构建；启动本地前端；检查 1440px、1024px、768px；检查控制台和可见布局问题；按验收结果修复。  
**验证：** 构建退出码为 0，三种视口无页面级横向溢出，主功能可访问。

## 执行顺序

```text
T1 → T2 → T3 → T4
  └──────→ T5 → T6 → T7
```

## 自检

- 每个计划模块至少对应一个任务。
- 依赖链无环，每个任务均有可执行的验证方式。
- 教学页和后端文件不在改动清单中。

