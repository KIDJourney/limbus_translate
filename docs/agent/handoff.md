# Handoff

本文档维护最近一次工作交接记录。每次完成实质性变更后，把本轮结果追加到顶部。

## 2026-06-13 — Limbus Translate 初版工具骨架

### 已完成

- 使用 `ai-workspace-init` 初始化 `/Users/kidjourney/Project/limbus_translate`，验证通过 31 个 Markdown 文件。
- 克隆并研究 LocalizeLimbusCompany 临时 checkout：`/tmp/limbus-translate-work/LocalizeLimbusCompany`。
- 新增 Python CLI 包 `limbus_translate`：
  - `scan`：扫描 `KR` 与 `LLC_zh-CN` 的待译单元。
  - `glossary sync-paratranz`：同步 Paratranz 项目 `6860` 术语。
  - `glossary import`：离线导入 CSV / JSON 术语。
  - `translate`：用 provider 生成同结构输出，默认 `dry-run`。
- 新增测试夹具和直接单元测试入口。
- 新增调研文档：[translation-framework.md](../research/translation-framework.md) 与 [localize-data-study.md](../tech/localize-data-study.md)。

### 验证状态

- `python3 -m limbus_translate.cli scan --source tests/fixtures/localize/KR --target tests/fixtures/localize/LLC_zh-CN --output /tmp/limbus-missing.json`：通过，输出 2 条。
- 直接调用 `tests.test_scanner` 和 `tests.test_glossary`：通过。
- `python3 -m limbus_translate.cli glossary sync-paratranz --page-size 1000 --output /tmp/limbus-paratranz.json`：通过，同步 1963 条。
- `python3 -m limbus_translate.cli translate ... --provider dry-run`：通过，输出同结构 JSON。
- 真实 Localize checkout 扫描：通过；默认输出 19 条 `target_same_as_source`，全部为 `StoryData/*.content` 高风险文本；`--include-internal` 可审计 263 条完整同源残留。
- `python3 -m pytest -q` 未运行成功，因为系统 Python 没有安装 `pytest`；已用无依赖直接测试替代。

### 风险

- 当前扫描仍按 JSON path 对齐，尚未实现 `dataList[*].id` 主键 adapter。
- 当前 QA 已覆盖韩文残留、占位符、标签、数字、换行和术语命中，但还没有长度、简繁和 MQM 分类。
- Chrome 插件连接 Paratranz 页面失败，但子任务已通过公开 API 证明术语可读；若要用 Chrome，需要用户允许打开 Chrome 窗口刷新扩展连接。

### 下一步

- 增加 `dataList[*].id` 主键 adapter，避免数组插入导致 JSON path 漂移。
- 增加简繁、长度、reviewed / locked 状态和 fuzzy TM。
- 建立 500-1000 条 gold set，用于模型赛马和 prompt 回归。

## 2026-06-09 — 文档骨架初版

### 已完成

- 创建根目录 `AGENTS.md`、`CLAUDE.md`、`README.md`。
- 创建 `docs/product/`、`docs/design/`、`docs/tech/`、`docs/test/`、`docs/verification/`、`docs/agent/`、`docs/templates/`。
- 创建最小文档验证脚本 `scripts/validate-docs.sh` 和 `Makefile` 入口。
- 将验证记录从 `docs/test/` 拆到 `docs/verification/`，支持按业务场景维护验证方法和证据。
- 创建 `scripts/init-ai-workspace.sh`，用于把模板复制到其他项目且不覆盖已有文件。
- 创建用户级 skill `ai-workspace-init`，用于让 Codex 按固定流程初始化 AI Workspace 文档结构。

### 验证状态

- `make validate-docs`：通过，输出见最新验证记录。

### 风险

- 当前只是文档系统初版，未绑定具体应用技术栈。
- 验证脚本只检查结构和链接，不检查内容质量。

### 下一步

- 根据用户观察反馈调整目录命名、文档粒度和模板。
- 如果确认结构可用，补充初始化脚本或真实应用代码目录。
