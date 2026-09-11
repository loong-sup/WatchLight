# Watchlight Evaluation: httpx-release-seed

Dataset version: `1.0`

## Summary

| Metric | Result |
| --- | ---: |
| Cases | 5 |
| Sources | 6 |
| Notification precision | 100.00% |
| Change recall | 100.00% |
| F1 | 100.00% |
| Duplicate compression | 33.33% |
| Expected fact coverage | 100.00% |
| False alerts / 100 cases | 0.00 |
| Processing latency P95 | 12.93 ms |

## Cases

| Case | Category | Expected | Predicted | Raw changes | Delivered |
| --- | --- | ---: | ---: | ---: | ---: |
| httpx-0281-release | meaningful_change | true | true | 1 | 1 |
| httpx-0281-duplicate | temporal_duplicate | false | false | 1 | 0 |
| httpx-0281-irrelevant | irrelevant_change | false | false | 1 | 0 |
| httpx-0281-unchanged | no_change | false | false | 0 | 0 |
| httpx-0281-cross-source | cross_source_duplicate | true | true | 2 | 1 |
