# Contributing

这是一个**个人知识库模板**，不是通用 Wiki 平台。贡献请优先帮助“让输入继续流动”，而不是增加结构。

## 开始前

1. 读 [AGENTS.md](AGENTS.md) 与 [`00 索引/设计取舍.md`](00%20索引/设计取舍.md)。
2. 用 Obsidian 打开仓库根目录作为 vault，确认你能复现问题。
3. 不要提交个人笔记、真实姓名、公司内部资料或 `.workbuddy/` 备份。

## 本地验证

```bash
python3 -m unittest discover -s tools/tests -v
python3 tools/kb_audit.py --strict
python3 tools/kb_clean_demo.py   # 只预览
```

Windows 上把 `python3` 换成 `python` 或 `py -3`。

## 接受什么

- 审计脚本的 bug / 误报修复，附带最小复现测试。
- 文档、模板、查询的可读性改进。
- 在**真实痛点**上简化结构，而不是增加结构。
- 跨平台兼容性修复（Windows / macOS / Linux）。

## 需要先讨论的

- 新增顶层目录、frontmatter 字段、查询块或社区插件。
- 改变 `status` / `type` / `source_type` / `form` 受控词表。
- 改变“只链接不复制”“状态诚实”“AI 不代填 `endorsed` / 不代勾 KR”等核心规则。
- 大规模移动或重命名文件。

请先开 issue，写清：现在卡在哪、为什么现有结构解决不了、代价是什么。没有真实痛点的“更完整”提案通常不会被接受。

## 审计检查

新增检查时：

1. 在 `tools/kb_audit.py` 写 `check_xxx(vault) -> CheckResult`。
2. 在 `run_audit()` 的 `checks` 列表注册。
3. 在 `tools/tests/` 加最小复现。
4. 更新 [`00 索引/审计说明.md`](00%20索引/审计说明.md)。

不要把“内容质量”“事实准确性”写进审计；那会让 FAIL 变成主观判断。

## 提交

- 一个 PR 只做一类改动。
- 提交信息用 `feat:` / `fix:` / `docs:` / `test:` / `chore:` 前缀。
- 提交前跑上面的测试与审计命令。
- 贡献内容默认以 [MIT](LICENSE) 授权。
