# Test Plan

本文档维护 Limbus Translate 当前测试策略和验收口径。

## 测试目标

1. 确认 JSON 扫描能识别目标缺失、目标为空、目标等于韩文源文的待译单元。
2. 确认 Paratranz 术语缓存能同步或离线导入。
3. 确认 dry-run 翻译能生成同结构输出 JSON。
4. 确认文档骨架和 Markdown 相对链接不损坏。

## 当前覆盖

| 测试 | 覆盖范围 | 命令 |
|---|---|---|
| 文档结构检查 | 根目录入口、关键目录、关键 README 是否存在 | `make validate-docs` |
| Markdown 链接检查 | `docs/` 和根目录入口中的相对 Markdown 链接 | `make validate-docs` |
| 直接单元测试 | 扫描器和术语匹配核心行为 | `make test` |
| CLI smoke | fixture 扫描和 dry-run 同结构输出 | `make smoke` |
| Paratranz smoke | 项目 `6860` 术语同步 | `make sync-glossary` |
| TODO / 待确认扫描 | 发现未解决问题和阻塞项 | `rg "TODO|待确认|阻塞" docs` |

## 验收标准

1. `make validate-docs` 通过。
2. `make test` 通过。
3. `make smoke` 通过，输出 `build/missing-units.json` 和 `build/LLC_zh-CN/Sample.json`。
4. `make sync-glossary` 能同步 1963 条左右术语；若 Paratranz API 不可用，应使用离线导入兜底。
5. 真实 Localize checkout 扫描结果需要人工审查，不能把内部标识直接当缺译上线。

## 回归要求

以下变化必须重新执行对应验证：

- 修改 `json_paths.py` 或 `scanner.py`：执行 `make test` 和真实 checkout 扫描。
- 修改 `glossary.py`：执行 `make test` 和 `make sync-glossary`。
- 修改 `translator.py` 或 provider：执行 `make smoke`。
- 修改文档或 Markdown 链接：执行 `make validate-docs`。
