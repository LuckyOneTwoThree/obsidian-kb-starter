# Troubleshooting

## 日记命令找不到

在 Obsidian 设置 → 核心插件里打开「日记 / Daily notes」。本库的 `.obsidian/daily-notes.json` 已经把目录指向 `01 收件箱/A 临时想法`，不需要改路径。

## 工作台查询块为空

- 属性过滤必须写成 `[status:待阅读]`，不能写成 `status:待阅读`。
- `path:"01 收件箱"` 里的目录名必须和实际文件夹一致。
- 查询块要放在 ` ```query ` 代码块里，不要放进普通代码块或引用块。
- 先用 Obsidian 全局搜索验证同一条件，再回来看查询块。

## 审计报错怎么读

- `A1` 断链：检查文件名、相对路径、大小写；唯一文件名可以只写 `[[文件名]]`。
- `A4` 锚点失效：锚点要逐字匹配标题；现在支持 ATX 和 Setext 标题。
- `A6` 文件名重复：包括仅大小写不同的 `Foo.md` / `foo.md`；Windows/macOS 上容易撞，改用前缀。
- `A8` 链接大小写不匹配：macOS/Windows 可能能打开，Linux 不一定；建议改成真实大小写。
- `B11` 布局不符：`source_type` / `area` / `form` 与子目录不一致。
- `B12` 常青卡缺 `form`：补 `form: 概念 / 原则 / 模型 / 方法 / 判断 / 金句`。
- `B13` 项目路径：项目主页必须是 `05 项目/<年份>/<年份-项目名>/<年份-项目名>-项目主页.md`。
- `B14` 已归档不在 `99 归档`：移动文件并保留链接。
- `B15` 别名与文件名冲突：改别名，或改用全路径链接。
- `C3` 项目已完成但没有复盘：在项目主页链接一篇 `type: review` 的复盘。
- `E3` 项目主页很久没更新：这是**文档新鲜度**提醒，不是项目死亡判决；用 git/交付物核实。
- `E4` 收件箱捕获超过两周：删掉、展开或归位，不要为了清队列改状态。

## 只想看摘要

```bash
python3 tools/kb_audit.py --summary
python3 tools/kb_audit.py --max-issues 30
```

`--json` 始终保留全量结果。`--strict` 会把 WARN 也当失败；如果只想阻断 FAIL，用普通模式。

## 清理示例后想恢复

`kb_clean_demo.py --apply` 会把受影响文件备份到 `.backup/demo-clean-<时间>/`。把备份里的文件复制回原路径即可；如果你用 git，也可以 `git restore` / `git checkout` 对应文件。

默认 dry-run 会跳过缺少 `示例` 标签或日记标记的文件；`--force` 才会强删，且仍会先备份。

## Windows

- 把 `python3` 换成 `python` 或 `py -3`。
- 文件名不能是 `CON` / `PRN` / `AUX` / `NUL` / `COM1` / `LPT1` 等保留名；`kb_new.py` 会拒绝。
- 推荐在终端设置 `PYTHONUTF8=1`，避免中文输出编码问题。

## 新建笔记提示文件名已存在

本库要求文件名全库唯一。改标题，或加前缀（如 `2026-`、项目名）。`--allow-duplicate` 只在你明确接受歧义链接时使用。

## 表单里 `area` / `source_type` / `form` 填什么

见 [`00 索引/受控词表.md`](00%20索引/受控词表.md)。`form` 只用于常青卡；`source_type` 用于 02/03/04 和项目主页。
