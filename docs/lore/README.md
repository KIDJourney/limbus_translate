# Lore Notes

本目录存放可导入 `cache/lore/world.json` 的世界观资料笔记。`lore import --input docs/lore` 会跳过本 README，并读取同目录下的 Markdown、JSON、JSONL、CSV 或 TXT 文件。

Markdown 推荐按一级到三级标题拆条目，在正文里用 `关键词:` 或 `anchors:` 标出召回锚点。

导入后可用 `lore index --lore cache/lore/world.json --output cache/lore/world-index.json` 构建离线 hashed-vector 索引，再用 `lore search --index cache/lore/world-index.json --query "..."` 检查召回结果。翻译命令传入 `--lore-index` 时会优先使用索引向 provider context 注入 lore 片段。
