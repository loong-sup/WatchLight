# Watchlight 真实数据评测

这套评测通过回放人工标注的历史网页快照，衡量 Watchlight 是否能发现值得通知的变化、过滤无关内容并压缩重复通知。回放器直接使用生产代码中的内容拦截、变化检测、价值过滤、跨来源合并和 72 小时去重逻辑。

## 快速验证

仓库内置的 smoke 数据集只用于验证评测程序，不可作为简历中的真实业务成绩：

```bash
python -m watchlight.evals evals/datasets/watchlight_smoke.jsonl
```

仓库还提供一组来自 HTTPX 官方 GitHub 仓库 0.28.0 与 0.28.1 标签的冻结 changelog，作为真实数据接入基线：

```bash
python -m watchlight.evals evals/datasets/httpx_release_seed.jsonl
```

该 seed 只有 2 份真实快照和 5 个标注场景，用于证明真实数据能够稳定回放，样本量仍不足以作为正式简历成绩。

报告默认输出到 `evals/reports/`，包括机器可读的 JSON 和便于审阅的 Markdown。

## 采集真实快照

选择 GitHub Release、产品公告、价格页等公开网页，在不同日期运行：

```bash
python -m watchlight.evals.capture \
  --url https://example.com/releases \
  --output-dir evals/captures/releases
```

采集器仅访问公开 HTTP(S) 地址，遵守 `robots.txt`，并拒绝登录页、验证码、付费墙和错误页。每次采集会保存原始 HTML、SHA-256 和采集时间。建议持续采集 2～4 周，并将定稿的数据快照纳入版本控制或不可变对象存储。

## 数据集格式

数据集采用 JSONL，每行代表一次任务执行：

```json
{
  "case_id": "github-release-2026-08-01",
  "task_id": "github-release-watch",
  "captured_at": 1785542400,
  "category": "meaningful_change",
  "trigger_condition": {
    "must_contain": ["released"],
    "must_not_contain": ["prerelease"]
  },
  "sources": [
    {
      "url": "https://github.com/org/repo/releases",
      "previous_path": "../captures/releases/previous.html",
      "current_path": "../captures/releases/current.html",
      "http_status": 200
    }
  ],
  "expected_notify": true,
  "expected_event_id": "repo-v2-release",
  "expected_facts": ["v2.0 released"]
}
```

快照路径相对于 JSONL 文件所在目录解析。多个来源属于同一次任务执行时，应放在同一个 `sources` 数组中，以评估跨来源合并效果。

## 标注规则

至少覆盖以下类别：

- `meaningful_change`：应当通知的版本、价格或政策变化；
- `no_change`：内容完全不变；
- `irrelevant_change`：页面变化但不符合关注条件；
- `cross_source_duplicate`：多个来源报道同一事件；
- `temporal_duplicate`：72 小时内重复出现的同一事件；
- `blocked_content`：登录页、验证码、付费墙或错误页。

建议两人独立判断 `expected_notify` 和 `expected_facts`，有分歧时复核。调参集与最终测试集必须分开；只有未参与规则调整的测试集结果才能写入简历。

## 报告指标

- `notification_precision`：发出的通知中真正有价值的比例；
- `change_recall`：所有应通知变化中被发现的比例；
- `f1`：准确率和召回率的调和平均；
- `duplicate_compression_rate`：通过跨源与时间窗口去重减少的候选通知比例；
- `fact_coverage`：人工标注关键事实在证据中被覆盖的比例；
- `false_alerts_per_100_cases`：每 100 次任务执行产生的错误通知数；
- `processing_ms_p95`：离线分析阶段 P95 处理耗时，不包含网络采集和模型调用。

## 简历数据门槛

正式报告建议至少包含 30 个任务、500 组快照和 3 类真实来源。简历应同时注明数据规模与测试方式，例如：

> 基于 32 个真实公开信息源构建 680 组历史快照评测集；有效通知准确率达到 XX%，变化召回率达到 XX%，跨来源与时间窗口去重使候选通知减少 XX%。

不要将 smoke 数据集的结果写入简历，也不要把离线处理耗时表述为端到端通知延迟。
