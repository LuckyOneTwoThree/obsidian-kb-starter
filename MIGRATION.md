# Migration

把已有 Obsidian 库迁到这个结构时，**不要直接覆盖现有 `.obsidian/`**。先备份或 commit。

## 推荐顺序

1. **备份**：`git commit`，或把整个库复制到外部存储。
2. **先当新库打开**：把 starter 复制到一个新目录，用 Obsidian 打开，确认目录、模板、查询块都正常。
3. **复制内容，不复制配置**：把已有笔记按流程位置放入 `01`–`04`、`05 项目`；不要复制旧库的 `.obsidian/workspace.json`、主题、插件数据。
4. **合并 Obsidian 配置**：只取你需要的键，合并到现有 `.obsidian/`：
   - `daily-notes.json` 的 folder/template
   - `templates.json` 的 folder
   - `app.json` 的附件目录 / 新建笔记目录
   - `core-plugins.json` 的日记、模板、属性
5. **改路径**：如果重命名了目录，同步修改 `tools/kb_config.json`、工作台查询、索引页、目录说明、`.obsidian/daily-notes.json`、`.obsidian/templates.json` 和 `tools/kb_new.py` 的目录映射。
6. **跑审计**：`python3 tools/kb_audit.py`。先修 FAIL；WARN 逐条判断，不要为了全绿改状态。
7. **清理示例**：`python3 tools/kb_clean_demo.py --apply`。确认索引和 README 的示例段已清理。
8. **观察一周**：旧库保留只读，确认新库的捕获、消化、判断链路真的在跑，再归档旧库。

## 迁移时最容易犯的错

- 把旧库的 20 个同名「项目主页」直接复制进来 → 先改名为 `<项目名>-项目主页.md`。
- 把所有旧标签一起搬进来 → 标签是检索工具，不是分类展览；先保留高频主题词。
- 把 `status: active` 的旧模板当笔记复制 → 模板放 `07 资料库/D 模板/`，不要进 02–05。
- 一次性搬 500 篇 → 先搬最近 30 天有真实动作的笔记，其余留在旧库归档。

迁移完成后，从 [`00 索引/开始使用.md`](00%20索引/开始使用.md) 重新走一遍 7 天路径。
