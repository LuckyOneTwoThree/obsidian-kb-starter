# Obsidian 知识库 Starter

[![CI](https://github.com/LuckyOneTwoThree/obsidian-kb-starter/actions/workflows/ci.yml/badge.svg)](https://github.com/LuckyOneTwoThree/obsidian-kb-starter/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](tools/kb_audit.py)
[![Obsidian 1.4+](https://img.shields.io/badge/Obsidian-1.4%2B-7c3aed.svg)](https://obsidian.md)
[![No community plugins](https://img.shields.io/badge/community%20plugins-0-2ea44f.svg)](#环境)

一套可以**今天就写下第一句话**的中文 Obsidian 知识库。8 个知识目录、7 个模板、4 个工作台视图、3 个命令行工具，零社区插件。

它不试图替你管理一切。它只保证一件事：**捕获足够轻，判断有地方落，输出有路径可走。**

**English** — A Chinese-first Obsidian knowledge-base starter that prioritizes capture over governance: 8 folders, 7 templates, zero community plugins, a standard-library audit with 53 tests, and an `AGENTS.md` contract for AI assistants.

![Obsidian 知识库 Starter](07%20资料库/A%20附件/banner.svg)

## 为什么做这个

大多数知识库模板解决的是「结构应该长什么样」，但真正让人放弃的通常不是结构，而是：

- 新建一条笔记要先选目录、选模板、填五个字段
- 收藏了很多，却从来没有形成自己的判断
- 库越整理越漂亮，但没有任何新输入
- 规则越写越多，最后连自己都不记得哪条有效

这套模板来自对一个长期维护的个人知识库的复盘（2026-10 的复盘快照）。那个库的机械指标几乎全绿：零断链、零孤儿、零 frontmatter 违规。但它连续 75 天没有一条新捕获，大量阅读笔记没有被转化成判断。

**结论是：治理不能替代输入。** 所以这个 Starter 把结构压到最小，把「开始写」的摩擦压到最低。

## 它和常见模板有什么不同

- **文件夹表示流程位置，不表示主题。** 02 是来源消化，03 是判断，04 是原子知识；主题靠标签和双链。
- **只链接，不复制。** 02 放来源，03 写因果链，04 放能独立成立的结论。
- **状态诚实。** `草稿` 是合法状态；02 的 `已沉淀` = 来源消化完，03 用 `已提炼`，04 的 `已沉淀` = 作者确认。
- **审计是证伪工具，不是评分。** FAIL 修结构，WARN 留给人判断；它不检查内容质量和事实准确性。
- **AI 有协作契约。** `AGENTS.md` 明确 AI 可以起草和整理，但不能代填 `endorsed`、代勾关键结果、批量改状态。
- **零社区插件。** 工作台用 Obsidian 原生嵌入搜索；审计只用 Python 标准库。

## 适合谁

- 中文 Obsidian 个人用户
- 经常阅读、需要把输入变成判断的产品经理、研究者、写作者
- 喜欢纯 Markdown、可迁移、不要插件锁定的人
- 愿意用命令行或 CI 做结构自检的人
- 想要一个能长期维护、而不是一次性搭得很大的库的人

## 不适合谁

- 团队 Wiki（需要权限、评审、多人协作）
- 任务管理 / 数据库（Obsidian 不是最好的工具）
- 想要几十个细分模板的人
- 已经有成熟工作流、只需要微调的人

## 30 秒开始

1. 在 GitHub 点 **Use this template**，或下载 ZIP；不要直接 fork，fork 会带上示例提交历史。
2. 用 Obsidian **打开文件夹作为 vault**，不是打开单个文件。
3. 按 `Cmd/Ctrl + P`，运行 **Daily notes: Open today's daily note**（中文界面为「日记：打开今天的日记」）。
4. 光标会落在 `01 收件箱/A 临时想法/` 的当天笔记里。写一句今天真实想过的话，没有格式要求。
5. 想检查结构时，在库根目录运行：

```bash
python3 tools/kb_audit.py
```

不需要安装任何 Python 依赖，标准库即可（Python 3.9+）。Windows 可把 `python3` 换成 `python` 或 `py -3`。

更细的上手路径见 [`00 索引/开始使用.md`](00%20索引/开始使用.md)。日常使用时，从 [`00 索引/知识库主页.md`](00%20索引/知识库主页.md) 开始：四个查询块就是你的维护视图。

## 它长什么样

```text
00 索引      导航、工作台、规则
01 收件箱    捕获（想法 / 剪藏 / 待读 / 待整理）
02 阅读笔记  对外部来源的消化
03 主题笔记  我的判断与因果链
04 常青笔记  可独立复用的原子知识
05 项目      有交付物的行动
07 资料库    模板与附件
99 归档      冷存储
tools        审计、新建、示例清理脚本
```

知识流：

```text
捕获 → 消化 → 判断 → 原子卡 → 项目 / 输出
 01      02      03      04        05
```

## 7 个模板

| 模板 | 用途 | 初始状态 |
|---|---|---|
| 临时想法 | 一句话捕获 | `待整理` |
| 阅读笔记 | 书 / 文章 / 课程消化 | `待阅读` |
| 主题笔记 | 我的判断 + 因果链 | `待提炼` |
| 常青卡 | 概念 / 原则 / 模型 / 方法 / 判断 / 金句 | `草稿` |
| 项目主页 | 有交付物的项目 | `待启动` |
| 复盘 | 项目或事件复盘 | `草稿` |
| 每周回顾 | 每周 30 分钟收口 | `草稿` |

模板里的 `status` 是**新建笔记的初始状态**，不是模板自己的状态。模板目录豁免审计。

## 工具

```bash
# 结构审计（只读）
python3 tools/kb_audit.py

# 严格模式（WARN 也返回非零，适合要求零 WARN 的库）
python3 tools/kb_audit.py --strict

# 机器可读
python3 tools/kb_audit.py --json

# 新建笔记
python3 tools/kb_new.py reading --title "某篇文章" --source-type 文章
python3 tools/kb_new.py evergreen --title "某个判断" --form 判断 --area 工作
python3 tools/kb_new.py daily

# 清理示例（默认 dry-run；--apply 才写入）
python3 tools/kb_clean_demo.py
python3 tools/kb_clean_demo.py --apply

# 单元 + 集成测试
python3 -m unittest discover -s tools/tests -v
```

`kb_new.py` 在写入前检查全库重名，`--force` 覆盖前会备份到 `.backup/`。`kb_clean_demo.py` 删除示例文件、清理索引与 README 示例段，并先备份。

审计检查六类东西：链接、frontmatter、可达性、消化链路、陈旧度、占位与空笔记。它**不**检查内容质量、事实准确性、外部链接是否存活、附件是否存在。边界见 [`00 索引/审计说明.md`](00%20索引/审计说明.md)。

## 五个设计原则

1. **先闭环，后覆盖。** 没有长期领域、发布流水线、覆盖率矩阵。等真实痛点出现再加。
2. **文件夹是流程位置，不是主题。** 主题靠标签和双链。
3. **只链接，不复制。** 02 放来源，03 写判断，04 放原子结论。
4. **状态必须诚实。** `草稿` 是合法状态；`已沉淀` 在 04 意味着作者确认过。
5. **治理冻结，输入优先。** 没有输入时，不加规则。

完整取舍见 [`00 索引/设计取舍.md`](00%20索引/设计取舍.md)。

## 30 天路径

- **第 1 天**：完成第一次捕获
- **第 7 天**：产出第一张常青卡（草稿即可）
- **第 30 天**：完成第一次对外输出（发给一个人也算）

成功判据不是「第一天零断链」，而是这三件事真的发生了。

## 示例内容

`01`–`05` 中带 `示例` 标签的笔记，以及 `2026-周报改造` 项目，全部是虚构的「远程团队协作」示例，用于演示一条完整链路。示例日记是 `01 收件箱/A 临时想法/2026-10-12.md`。

读法见 [`00 索引/示例导览.md`](00%20索引/示例导览.md)。删除推荐用脚本：

```bash
python3 tools/kb_clean_demo.py            # 预览
python3 tools/kb_clean_demo.py --apply    # 删除并清理索引，先自动备份
```

## 用 AI 协作

把 `AGENTS.md` 放在库根。支持 `AGENTS.md` 的工具（如 Codex / Qoder）会先读它；Claude Code 会自动读 [CLAUDE.md](CLAUDE.md)，后者指向 `AGENTS.md`；其他工具可以把文件内容贴进会话。

AI 可以：整理收件箱、起草阅读/主题/常青笔记、补链接、跑审计、解释 WARN。

AI 不可以：代填 `endorsed`、代勾关键结果、批量改 `status`、伪造 `source_url` / `source_type`、未确认就标 `已沉淀`。

示例 prompt：

```text
先读 AGENTS.md。整理 01 收件箱，先给方案，不要动文件。
把这篇 02 阅读笔记提拔为 03/04，先检查 03 是否已有同一判断。
跑 python3 tools/kb_audit.py，解释所有 WARN，但不要为了全绿改状态。
```

## 自定义 / 迁移

- **改词表 / 路径**：`tools/kb_config.json`，同时更新 [`00 索引/受控词表.md`](00%20索引/受控词表.md)。
- **改模板**：`07 资料库/D 模板/`，同时更新模板库、`.obsidian/templates.json` 与配置。
- **改工作台查询**：`00 索引/知识库主页.md`，保持 `[status:值]` 的方括号语法。
- **改目录名**：不要只改文件夹。配置、查询、索引、文档、`.obsidian/daily-notes.json`、`.obsidian/templates.json` 与 `tools/kb_new.py` 的目录映射都要一起改。
- **已有 vault**：先把这个仓库当新 vault 打开，确认喜欢再合并；不要直接覆盖现有 `.obsidian/`。合并时只取 `app.json` / `daily-notes.json` / `templates.json` 中需要的键。

## FAQ

**为什么不用 Dataview？**
工作台用 Obsidian 原生嵌入搜索，零插件依赖。等你明确知道哪个视图不够用，再引入 Dataview / Bases。

**示例内容会影响我的捕获吗？**
示例笔记带 `示例` 标签，示例日记固定在过去的日期，不会占用今天的日记；用 `tools/kb_clean_demo.py --apply` 可以一次移除。

**能在手机上用吗？**
可以捕获和阅读；`tools/` 下的 Python 脚本需要桌面端或任何有 Python 3.9+ 的环境。

**`草稿` 是不是没写完？**
不是。`草稿` 表示内容已成形、但作者还没确认；AI 协作产出尤其应该从这里开始。

**审计能保证知识库健康吗？**
不能。它只检查结构是否遵守自己写的规则；输入是否持续、判断是否成立，需要你自己回答。

**为什么文件夹名和状态是中文？**
目标用户是中文个人知识库使用者。想改英文，按「自定义」一节同步改配置、查询、模板和文档即可。

**这个项目维护吗？**
v0.1 是一个可用的最小闭环，按 issue 和真实痛点做 best-effort 维护；不承诺大而全的路线图。

## 环境

- Obsidian 1.4+（桌面或移动端；建议桌面端做初始设置）
- Python 3.9+（仅工具需要；不用工具也可以纯手工使用）
- 零社区插件

## 版本与许可

当前为 **v0.1.0**。变更见 [CHANGELOG.md](CHANGELOG.md)。

文本、结构、脚本与示例以 [MIT](LICENSE) 授权。

示例内容为虚构，不含第三方版权材料。

引用外部来源时请遵守原作者授权。Obsidian 是其权利人的商标，本项目与 Obsidian 官方无隶属关系。

贡献前请读 [CONTRIBUTING.md](CONTRIBUTING.md)。安全问题见 [SECURITY.md](SECURITY.md)。

## 文档导航

- [`00 索引/开始使用.md`](00%20索引/开始使用.md)：5 分钟上手，7 天写出第一张卡
- [`00 索引/知识库主页.md`](00%20索引/知识库主页.md)：每天的工作台
- [`00 索引/知识库地图.md`](00%20索引/知识库地图.md)：东西该往哪放
- [`00 索引/受控词表.md`](00%20索引/受控词表.md)：`type` / `status` / `source_type` / `form`
- [`00 索引/维护手册.md`](00%20索引/维护手册.md)：每周 30 分钟、每月 2 小时
- [`00 索引/审计说明.md`](00%20索引/审计说明.md)：审计边界与检查项
- [`00 索引/设计取舍.md`](00%20索引/设计取舍.md)：为什么是现在这个形状
- [`00 索引/升级路线.md`](00%20索引/升级路线.md)：以后可以加什么
- [`07 资料库/D 模板/模板库.md`](07%20资料库/D%20模板/模板库.md)：7 个模板的用途
- [AGENTS.md](AGENTS.md)：给 AI 助手的协作契约
