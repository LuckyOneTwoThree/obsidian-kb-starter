#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从模板创建一篇新笔记。

用法：
    python3 tools/kb_new.py daily
    python3 tools/kb_new.py reading --title "某篇文章" --source-type 文章
    python3 tools/kb_new.py topic --title "某个主题" --area 工作
    python3 tools/kb_new.py evergreen --title "某个判断" --form 判断
    python3 tools/kb_new.py project --title "周报改造"
    python3 tools/kb_new.py review --title "某项目复盘"
    python3 tools/kb_new.py weekly
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from kb_audit import ConfigError, Vault, load_config, parse_frontmatter, resolve_root


VERSION = "0.1.0"


KIND_TO_TEMPLATE = {
    "daily": "_模板_临时想法.md",
    "reading": "_模板_阅读笔记.md",
    "topic": "_模板_主题笔记.md",
    "evergreen": "_模板_常青卡.md",
    "project": "_模板_项目主页.md",
    "review": "_模板_复盘.md",
    "weekly": "_模板_每周回顾.md",
}

KIND_TO_TYPE = {
    "daily": "inbox",
    "reading": "reading",
    "topic": "topic",
    "evergreen": "evergreen",
    "project": "project",
    "review": "review",
    "weekly": "review",
}

FORM_DIRS = {
    "概念": "A 概念",
    "原则": "B 原则",
    "模型": "C 模型",
    "方法": "D 方法",
    "判断": "E 判断",
    "金句": "F 金句",
}

AREA_DIRS = {
    "工作": "A 工作",
    "学习": "B 学习",
    "生活": "C 生活",
}

SOURCE_DIRS = {
    "书籍": "A 书籍",
    "文章": "B 文章",
    "课程": "C 课程",
    "播客": "D 其他",
    "视频": "D 其他",
    "论文": "D 其他",
    "网页": "D 其他",
}

INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|#^\[\]\x00-\x1f\x7f]')
WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


class NewNoteError(Exception):
    """无法创建笔记。"""


def sanitize_filename(value: str) -> str:
    value = re.sub(r"(?:\.md)+$", "", value.strip(), flags=re.I)
    value = INVALID_FILENAME_CHARS.sub("-", value)
    value = re.sub(r"\s+", " ", value).strip(" .-")
    if not value:
        raise NewNoteError("标题清洗后为空，请换一个标题。")
    if len(value) > 80:
        value = value[:80].rstrip(" .-")
    if value.upper() in WINDOWS_RESERVED:
        raise NewNoteError(
            f"标题 {value!r} 是 Windows 保留名，请换一个标题。"
        )
    return value


def find_name_conflicts(
    root: Path, config: Dict[str, object], rel: Path
) -> List[str]:
    """返回与目标文件名/别名冲突的库内文件。"""
    stem = Path(rel.name).stem
    vault = Vault(root, config)
    target = rel.as_posix()
    conflicts = set(vault.basename_index.get(stem, []))
    conflicts.update(vault.basename_casefold_index.get(stem.casefold(), []))
    conflicts.update(vault.alias_index.get(stem, []))
    conflicts.discard(target)
    return sorted(conflicts)


def backup_existing(root: Path, rel: Path) -> Path:
    """覆盖前把旧文件复制到 .backup/，返回备份路径。"""
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_path = root / ".backup" / f"kb_new-{stamp}" / rel
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / rel, backup_path)
    return backup_path


def parse_date(value: Optional[str]) -> _dt.date:
    if not value:
        return _dt.date.today()
    try:
        return _dt.date.fromisoformat(value)
    except ValueError as error:
        raise NewNoteError(f"--date 不是合法日期：{value}") from error


def default_title(kind: str, date: _dt.date) -> str:
    if kind == "daily":
        return date.isoformat()
    if kind == "weekly":
        iso = date.isocalendar()
        return f"{iso.year}-W{iso.week:02d} 周回顾"
    return ""


def destination(
    kind: str,
    title: str,
    date: _dt.date,
    year: int,
    area: str,
    source_type: str,
    form: str,
    override_dir: Optional[str],
) -> Tuple[Path, str]:
    """返回 (相对路径, 用于模板 {{title}} 的标题)。"""
    filename = f"{sanitize_filename(title)}.md"
    target_filename = filename
    template_title = sanitize_filename(title)

    if kind == "daily":
        target_filename = f"{date.isoformat()}.md"
        rel = Path("01 收件箱") / "A 临时想法" / target_filename
    elif kind == "reading":
        sub = SOURCE_DIRS.get(source_type, "B 文章")
        rel = Path("02 阅读笔记") / sub / target_filename
    elif kind == "topic":
        sub = AREA_DIRS.get(area, "A 工作")
        rel = Path("03 主题笔记") / sub / target_filename
    elif kind == "evergreen":
        sub = FORM_DIRS.get(form, "E 判断")
        rel = Path("04 常青笔记") / sub / target_filename
    elif kind == "project":
        project_name = template_title
        prefix = f"{year}-"
        if project_name.startswith(prefix):
            project_name = project_name[len(prefix):]
        if not project_name:
            raise NewNoteError("项目标题不能只有年份。")
        project_name = sanitize_filename(project_name)
        folder = f"{year}-{project_name}"
        target_filename = f"{folder}-项目主页.md"
        rel = Path("05 项目") / str(year) / folder / target_filename
        template_title = project_name
    elif kind in ("review", "weekly"):
        sub = AREA_DIRS.get(area, "A 工作")
        rel = Path("03 主题笔记") / sub / target_filename
    else:
        raise NewNoteError(f"未知的笔记类型：{kind}")

    if override_dir:
        override = Path(override_dir)
        if override.is_absolute() or ".." in override.parts:
            raise NewNoteError("--dir 必须是库内的相对路径，且不能包含 ..")
        rel = override / target_filename

    return rel, template_title


def validate_target_dir(
    root: Path, config: Dict[str, object], rel: Path, kind: str
) -> None:
    """拒绝会制造结构脏数据的 --dir / 默认路径。"""
    if not rel.parts:
        raise NewNoteError("目标路径为空。")

    parts = rel.parts
    skip_dirs = {str(item) for item in config.get("skip_dirs", [])}
    if any(part in skip_dirs or part.startswith(".") for part in parts[:-1]):
        raise NewNoteError("目标目录在跳过目录/隐藏目录内，拒绝写入。")

    top = parts[0]
    note_type = KIND_TO_TYPE.get(kind, "")
    if top == "01 收件箱":
        if note_type != "inbox":
            raise NewNoteError("01 收件箱只允许创建 inbox 类型笔记。")
    elif top == "99 归档":
        raise NewNoteError("请先用 kb_new 创建活跃笔记，再按归档流程移入 99 归档。")
    else:
        expected = config.get("expected_types_by_dir", {})
        allowed = expected.get(top) if isinstance(expected, dict) else None
        if allowed is None:
            raise NewNoteError(f"--dir 的顶层目录 {top!r} 不受支持。")
        if note_type not in allowed:
            raise NewNoteError(
                f"{top!r} 不允许 type {note_type!r}；允许：{', '.join(allowed)}"
            )

    if kind == "project":
        if (
            len(parts) != 4
            or parts[0] != "05 项目"
            or not re.fullmatch(r"\d{4}", parts[1])
            or not parts[2].startswith(parts[1] + "-")
            or parts[3] != f"{parts[2]}-项目主页.md"
        ):
            raise NewNoteError(
                "项目路径必须是 05 项目/<年份>/<年份-项目名>/<年份-项目名>-项目主页.md"
            )

    target = (root / rel).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as error:
        raise NewNoteError("目标路径解析后越出知识库根目录。") from error


def set_field(text: str, field: str, value: str) -> str:
    pattern = re.compile(rf"^{re.escape(field)}:[^\n]*$", re.M)
    if pattern.search(text):
        return pattern.sub(f"{field}: {value}", text, count=1)
    return re.sub(
        r"^(type:.*)$",
        lambda match: f"{match.group(1)}\n{field}: {value}",
        text,
        count=1,
        flags=re.M,
    )


def render_template(
    template: str,
    kind: str,
    title: str,
    date: _dt.date,
    year: int,
    area: str,
    source_type: str,
    form: str,
    status_override: Optional[str],
    config: Dict[str, object],
) -> str:
    now = _dt.datetime.now()

    def date_repl(match: "re.Match[str]") -> str:
        fmt = match.group(1)
        if not fmt:
            return date.isoformat()
        tokens = {
            "YYYY": f"{date.year:04d}",
            "MM": f"{date.month:02d}",
            "DD": f"{date.day:02d}",
            "HH": f"{now.hour:02d}",
            "mm": f"{now.minute:02d}",
            "ss": f"{now.second:02d}",
        }
        result = fmt
        for token, value in tokens.items():
            result = result.replace(token, value)
        return result

    text = re.sub(r"\{\{date(?::([^}]+))?\}\}", date_repl, template)
    replacements = {
        "{{title}}": title,
        "{{year}}": str(year),
        "{{area}}": area,
        "{{source_type}}": source_type,
        "{{form}}": form,
        "{{time}}": now.strftime("%H:%M"),
    }
    for placeholder, value in replacements.items():
        text = text.replace(placeholder, value)

    if status_override:
        fm, _ = parse_frontmatter(text)
        typ = fm.get("type", "")
        allowed = config.get("status_by_type", {}).get(typ, [])
        if allowed and status_override not in allowed:
            raise NewNoteError(
                f"status {status_override!r} 不适用于 type {typ!r}；"
                f"可选：{', '.join(allowed)}"
            )
        text = set_field(text, "status", status_override)

    if source_type and kind in ("reading", "topic", "evergreen", "project"):
        text = set_field(text, "source_type", source_type)
    if form and kind == "evergreen":
        text = set_field(text, "form", form)
    if area:
        text = set_field(text, "area", area)

    return text.rstrip() + "\n"


def next_step(kind: str) -> str:
    return {
        "daily": "一句话就够。记得本周回看一次。",
        "reading": "读完把 status 改为 已沉淀；在 00 索引/笔记索引.md 加一行。",
        "topic": "补因果链与证据锚点，完成后改 已提炼；在笔记索引加一行。",
        "evergreen": "确认判断成立后改 已沉淀 并填 endorsed；在笔记索引加一行。",
        "project": "填目标、关键结果与下一步；关键结果由你勾选；在项目总览加一行。",
        "review": "按小节回答，不要写流水账。",
        "weekly": "每周 30 分钟，只回答四件事。",
    }.get(kind, "在 Obsidian 中打开，补全内容。")


def run(args: argparse.Namespace) -> int:
    config_path = (
        Path(args.config).expanduser().resolve()
        if args.config
        else Path(__file__).resolve().parent / "kb_config.json"
    )
    config = load_config(config_path)
    root = resolve_root(config_path, config, args.root)

    if not root.is_dir():
        raise NewNoteError(f"知识库根目录不存在：{root}")

    kind = args.kind
    if kind not in KIND_TO_TEMPLATE:
        raise NewNoteError(
            "未知类型：%s；可选：%s" % (kind, ", ".join(KIND_TO_TEMPLATE))
        )

    date = parse_date(args.date)
    year = args.year or date.year
    if year < 2000 or year > 2100:
        raise NewNoteError("--year 必须在 2000–2100 之间。")

    title = args.title or default_title(kind, date)
    if not title:
        raise NewNoteError(f"{kind} 需要 --title。")

    area = args.area or ("工作" if kind in ("topic", "review", "weekly") else "")
    source_type = args.source_type or {
        "reading": "文章",
        "topic": "阅读笔记",
        "evergreen": "阅读笔记",
        "project": "原创随笔",
    }.get(kind, "")
    form = args.form or ("判断" if kind == "evergreen" else "")

    source_vocab = set(config.get("source_type_vocab", []))
    if source_type and source_type not in source_vocab:
        raise NewNoteError(
            "source_type %r 不在词表内；可选：%s"
            % (source_type, ", ".join(sorted(source_vocab)))
        )
    if form and form not in FORM_DIRS:
        raise NewNoteError(
            "form %r 不合法；可选：%s" % (form, ", ".join(FORM_DIRS))
        )

    templates_dir = root / str(config.get("templates_dir", "07 资料库/D 模板"))
    template_path = templates_dir / KIND_TO_TEMPLATE[kind]
    if not template_path.is_file():
        raise NewNoteError(f"找不到模板：{template_path}")

    rel, template_title = destination(
        kind,
        title,
        date,
        year,
        area,
        source_type,
        form,
        args.dir,
    )
    validate_target_dir(root, config, rel, kind)
    target = root / rel

    exists = target.exists()
    if exists and not args.force and not args.dry_run:
        raise NewNoteError(f"目标已存在：{rel}；如需覆盖请加 --force。")

    conflicts = find_name_conflicts(root, config, rel)
    if conflicts and not args.allow_duplicate:
        raise NewNoteError(
            "文件名已存在：%s；请改用「前缀-名称」或加 --allow-duplicate。冲突：%s"
            % (Path(rel.name).stem, ", ".join(conflicts))
        )
    if conflicts:
        print("警告：文件名重复（--allow-duplicate）：" + ", ".join(conflicts))

    template = template_path.read_text(encoding="utf-8")
    display_title = f"{year}-{template_title}" if kind == "project" else template_title
    rendered = render_template(
        template,
        kind,
        display_title,
        date,
        year,
        area,
        source_type,
        form,
        args.status,
        config,
    )

    if args.dry_run:
        if exists:
            print(f"将创建（目标已存在，--force 才会覆盖）：{rel}")
        else:
            print(f"将创建：{rel}")
        print("（--dry-run，未写入）")
        return 0

    if exists and args.force:
        backup_path = backup_existing(root, rel)
        print(f"已备份：{backup_path.relative_to(root).as_posix()}")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8")
    print(f"已创建：{rel}")
    print(f"下一步：{next_step(kind)}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="从模板创建一篇新笔记")
    parser.add_argument(
        "kind",
        choices=sorted(KIND_TO_TEMPLATE.keys()),
        help="笔记类型",
    )
    parser.add_argument("--title", help="标题；daily/weekly 可省略")
    parser.add_argument("--area", help="领域：工作 / 学习 / 生活")
    parser.add_argument("--source-type", dest="source_type", help="来源类型")
    parser.add_argument("--form", help="常青卡形态：概念 / 原则 / 模型 / 方法 / 判断 / 金句")
    parser.add_argument("--year", type=int, help="项目年份，默认取 --date 的年份")
    parser.add_argument("--status", help="初始状态，默认取模板")
    parser.add_argument("--dir", help="自定义目录（库内相对路径）")
    parser.add_argument("--date", help="日期 YYYY-MM-DD，默认今天")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--root", help="知识库根目录")
    parser.add_argument("--dry-run", action="store_true", help="只显示目标路径，不写入")
    parser.add_argument("--force", action="store_true", help="覆盖已存在文件（先备份到 .backup/）")
    parser.add_argument(
        "--allow-duplicate",
        action="store_true",
        help="允许与全库已有文件重名（默认拒绝）",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    args = parser.parse_args(argv)

    try:
        return run(args)
    except (ConfigError, NewNoteError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
