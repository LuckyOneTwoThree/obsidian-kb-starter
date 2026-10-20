# Releasing

发布前按顺序检查。

## 1. 版本与变更

- 更新 `CHANGELOG.md`，写清 Added / Changed / Fixed / Safety。
- 更新 README 的版本号、测试数量、banner 上的测试数量。
- 确认 `vX.Y.Z` 与 CHANGELOG 对应。

## 2. 本地验证

```bash
python3 -m unittest discover -s tools/tests -v
python3 tools/kb_audit.py --strict
python3 tools/kb_clean_demo.py   # dry-run
```

再在 Obsidian 桌面端打开一次：日记、四个查询块、模板插入、README 图片。

## 3. 发布

```bash
git add -A
git commit -m "release: vX.Y.Z"
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin main --tags
```

## 4. GitHub 设置

- 用 tag 创建 Release，正文从 CHANGELOG 摘取。
- Settings → Template repository 勾选。
- About → Description / Topics / Social preview：
  - Description：`中文优先的 Obsidian 知识库模板：捕获 → 消化 → 判断 → 原子卡。零社区插件，自带审计与 AGENTS.md AI 协作契约。`
  - Topics：`obsidian`, `obsidian-template`, `obsidian-vault`, `pkm`, `zettelkasten`, `knowledge-management`, `note-taking`, `markdown`, `python`, `chinese`, `ai-agents`, `productivity`
  - Social preview：1280×640 PNG（SVG 通常不被接受）。
- 补一张真实 Obsidian 截图或 GIF；banner 是视觉示意，不是使用证据。

## 5. 发布后

- 确认 CI badge 变为 passing。
- 检查 Release 的 source zip 能打开，README/模板/脚本都在。
- 记录下一版要修的真实痛点；没有痛点不要加结构。
