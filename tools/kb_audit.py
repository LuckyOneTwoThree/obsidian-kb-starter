#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""知识库结构审计（只读）。

检查链接、frontmatter、可达性、消化链路、陈旧度、占位符。
不检查内容质量、事实准确性、外部 URL 是否存活。

用法：
    python3 tools/kb_audit.py
    python3 tools/kb_audit.py --strict
    python3 tools/kb_audit.py --json
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import posixpath
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# 解析
# ---------------------------------------------------------------------------

FM_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.S)
FENCE_RE = re.compile(r"```.*?```|~~~.*?~~~", re.S)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
WIKILINK_RE = re.compile(r"(?<!!)\[\[([^\]]+)\]\]")
EMBED_RE = re.compile(r"!\[\[([^\]]+)\]\]")
HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
SPACE_RE = re.compile(r"\s+")


class ConfigError(Exception):
    """配置或运行环境错误。"""


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _parse_inline_list(value: str) -> List[str]:
    inner = value.strip()[1:-1].strip()
    if not inner:
        return []
    return [_strip_quotes(part) for part in inner.split(",") if part.strip()]


def parse_frontmatter(raw: str) -> Tuple[Dict[str, object], str]:
    """返回 (frontmatter dict, 正文)。不依赖 PyYAML。"""
    match = FM_RE.match(raw)
    if not match:
        return {}, raw

    block = match.group(1)
    body = raw[match.end():]
    fm: Dict[str, object] = {}
    lines = block.splitlines()
    index = 0

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            index += 1
            continue

        key_match = re.match(r"^([A-Za-z_][\w-]*):[ \t]*(.*)$", line)
        if not key_match:
            index += 1
            continue

        key, value = key_match.group(1), key_match.group(2).strip()
        if value == "":
            items: List[str] = []
            probe = index + 1
            while probe < len(lines):
                item_match = re.match(r"^\s+-\s+(.*)$", lines[probe])
                if not item_match:
                    break
                items.append(_strip_quotes(item_match.group(1)))
                probe += 1
            if items:
                fm[key] = items
                index = probe
                continue
            fm[key] = ""
        elif value.startswith("[") and value.endswith("]"):
            fm[key] = _parse_inline_list(value)
        else:
            fm[key] = _strip_quotes(value)
        index += 1

    return fm, body


def is_empty(value: object) -> bool:
    return value is None or value == "" or value == [] or value == {}


def strip_fenced(text: str) -> str:
    return FENCE_RE.sub("", text)


def strip_inline_code(text: str) -> str:
    return INLINE_CODE_RE.sub("", text)


def strip_comments(text: str) -> str:
    return HTML_COMMENT_RE.sub("", text)


def strip_ignored_lines(text: str, prefixes: Iterable[str]) -> str:
    prefixes = [p for p in prefixes if p]
    if not prefixes:
        return text
    pattern = re.compile(
        r"^\s*(?:>\s*)*(?:" + "|".join(re.escape(p) for p in prefixes) + r")"
    )
    return "\n".join(line for line in text.splitlines() if not pattern.match(line))


def make_linkable(text: str, ignore_prefixes: Iterable[str]) -> str:
    text = strip_fenced(text)
    text = strip_inline_code(text)
    text = strip_comments(text)
    text = strip_ignored_lines(text, ignore_prefixes)
    return text


def normalize_heading(value: str) -> str:
    value = re.sub(r"[ \t]+#+[ \t]*$", "", value.strip())
    value = SPACE_RE.sub(" ", value)
    value = PUNCT_RE.sub("", value)
    return value.lower().strip()


def extract_headings(body: str) -> List[str]:
    headings: List[str] = []
    for line in strip_fenced(body).splitlines():
        match = HEADING_RE.match(line.lstrip())
        if match:
            heading = re.sub(r"[ \t]+#+[ \t]*$", "", match.group(2)).strip()
            if heading:
                headings.append(heading)
    return headings


def is_under(rel: str, prefix: str) -> bool:
    prefix = prefix.rstrip("/")
    return rel == prefix or rel.startswith(prefix + "/")


def under_any(rel: str, prefixes: Iterable[str]) -> bool:
    return any(is_under(rel, prefix) for prefix in prefixes if prefix)


def top_dir(rel: str) -> str:
    return rel.split("/", 1)[0] if "/" in rel else ""


def is_date(value: str) -> bool:
    if not DATE_RE.match(value):
        return False
    try:
        _dt.date.fromisoformat(value)
        return True
    except ValueError:
        return False


def days_since(value: object) -> Optional[int]:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = _dt.date.fromisoformat(value[:10])
    except ValueError:
        return None
    return (_dt.date.today() - parsed).days


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


@dataclass
class Issue:
    code: str
    severity: str
    message: str
    path: str = ""

    def as_dict(self) -> Dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "path": self.path,
        }


@dataclass
class CheckResult:
    id: str
    name: str
    errors: List[Issue] = field(default_factory=list)
    warnings: List[Issue] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.errors:
            return "fail"
        if self.warnings:
            return "warn"
        return "pass"

    def add_error(self, code: str, message: str, path: str = "") -> None:
        self.errors.append(Issue(code, "error", message, path))

    def add_warning(self, code: str, message: str, path: str = "") -> None:
        self.warnings.append(Issue(code, "warning", message, path))


@dataclass
class AuditReport:
    root: str
    checks: List[CheckResult]
    stats: Dict[str, object] = field(default_factory=dict)

    @property
    def errors(self) -> int:
        return sum(len(check.errors) for check in self.checks)

    @property
    def warnings(self) -> int:
        return sum(len(check.warnings) for check in self.checks)

    @property
    def status(self) -> str:
        if self.errors:
            return "fail"
        if self.warnings:
            return "warn"
        return "pass"

    def by_code(self, code: str) -> List[Issue]:
        return [
            issue
            for check in self.checks
            for issue in check.errors + check.warnings
            if issue.code == code
        ]

    def to_dict(self) -> Dict[str, object]:
        return {
            "root": self.root,
            "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
            "summary": {
                "status": self.status,
                "errors": self.errors,
                "warnings": self.warnings,
            },
            "stats": self.stats,
            "checks": [
                {
                    "id": check.id,
                    "name": check.name,
                    "status": check.status,
                    "errors": [issue.as_dict() for issue in check.errors],
                    "warnings": [issue.as_dict() for issue in check.warnings],
                }
                for check in self.checks
            ],
        }


@dataclass
class FileInfo:
    rel: str
    path: Path
    raw: str
    fm: Dict[str, object]
    body: str
    linkbody: str
    headings: List[str]
    heading_norms: Set[str]
    outlinks: Set[str] = field(default_factory=set)
    inlinks: Set[str] = field(default_factory=set)


# ---------------------------------------------------------------------------
# 库加载与链接解析
# ---------------------------------------------------------------------------


class Vault:
    def __init__(self, root: Path, config: Dict[str, object]):
        self.root = root
        self.config = config
        self.files: Dict[str, FileInfo] = {}
        self.path_index: Dict[str, str] = {}
        self.basename_index: Dict[str, List[str]] = {}
        self.alias_index: Dict[str, List[str]] = {}
        self.read_errors: List[Tuple[str, str]] = []

        self.skip_dirs = set(config.get("skip_dirs", []))
        self.link_exempt = config.get("link_exempt_prefixes", [])
        self.ignore_prefixes = config.get("ignore_line_prefixes", [])

        self._load()

    def _load(self) -> None:
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = sorted(
                name
                for name in dirnames
                if name not in self.skip_dirs and not name.startswith(".")
            )
            for filename in sorted(filenames):
                if not filename.endswith(".md"):
                    continue
                path = Path(dirpath) / filename
                rel = path.relative_to(self.root).as_posix()
                try:
                    raw = path.read_text(encoding="utf-8")
                except UnicodeDecodeError as error:
                    self.read_errors.append((rel, str(error)))
                    continue
                raw = raw.lstrip("\ufeff")
                fm, body = parse_frontmatter(raw)
                headings = extract_headings(body)
                linkbody = (
                    ""
                    if under_any(rel, self.link_exempt)
                    else make_linkable(body, self.ignore_prefixes)
                )
                info = FileInfo(
                    rel=rel,
                    path=path,
                    raw=raw,
                    fm=fm,
                    body=body,
                    linkbody=linkbody,
                    headings=headings,
                    heading_norms={normalize_heading(h) for h in headings},
                )
                self.files[rel] = info
                self.path_index[rel[:-3]] = rel

        for rel in self.files:
            basename = posixpath.basename(rel[:-3])
            self.basename_index.setdefault(basename, []).append(rel)

        for rel, info in self.files.items():
            aliases = info.fm.get("aliases", [])
            if isinstance(aliases, str):
                aliases = [aliases] if aliases else []
            if isinstance(aliases, list):
                for alias in aliases:
                    if isinstance(alias, str) and alias.strip():
                        self.alias_index.setdefault(alias.strip(), []).append(rel)
            name_key = posixpath.basename(rel[:-3])
            self.alias_index.setdefault(name_key, []).append(rel)

    def resolve(self, target: str, src_rel: str) -> Tuple[Optional[str], str]:
        """按 Obsidian 的顺序解析：精确路径 → 相对当前目录 → 相对库根 → basename/alias。"""
        raw = target.strip().replace("\\", "/")
        if raw.endswith(".md"):
            raw = raw[:-3]
        if raw.startswith("/"):
            raw = raw.lstrip("/")
        if not raw:
            return None, "self"

        if raw in self.path_index:
            return self.path_index[raw], "path"

        src_dir = posixpath.dirname(src_rel)
        if src_dir:
            candidate = posixpath.normpath(posixpath.join(src_dir, raw))
            if candidate in self.path_index:
                return self.path_index[candidate], "path"

        candidate = posixpath.normpath(raw)
        if candidate in self.path_index:
            return self.path_index[candidate], "path"

        basename = posixpath.basename(raw)
        if "/" not in raw:
            hits = self.basename_index.get(basename, [])
            if len(hits) == 1:
                return hits[0], "basename"
            if len(hits) > 1:
                return None, "ambiguous"

            hits = self.alias_index.get(raw, [])
            if len(hits) == 1:
                return hits[0], "alias"
            if len(hits) > 1:
                return None, "ambiguous"
        else:
            hits = self.basename_index.get(basename, [])
            if len(hits) == 1:
                return hits[0], "half_path"
            if len(hits) > 1:
                return None, "ambiguous"

        return None, "broken"

    @staticmethod
    def iter_links(linkbody: str) -> Iterable[Tuple[str, str]]:
        for match in WIKILINK_RE.finditer(linkbody):
            raw = match.group(1).replace("\\|", "|")
            if "|" in raw:
                target = raw.split("|", 1)[0]
            else:
                target = raw
            target = target.strip()
            if target.startswith("#"):
                yield "", target[1:].strip()
                continue
            if "#" in target:
                file_part, anchor = target.split("#", 1)
                yield file_part.strip(), anchor.strip()
            else:
                yield target, ""

    @staticmethod
    def iter_embeds(linkbody: str) -> Iterable[Tuple[str, str]]:
        for match in EMBED_RE.finditer(linkbody):
            raw = match.group(1).replace("\\|", "|")
            if "|" in raw:
                target = raw.split("|", 1)[0]
            else:
                target = raw
            target = target.strip()
            if target.startswith("#"):
                yield "", target[1:].strip()
                continue
            if "#" in target:
                file_part, anchor = target.split("#", 1)
                yield file_part.strip(), anchor.strip()
            else:
                yield target, ""


# ---------------------------------------------------------------------------
# 检查
# ---------------------------------------------------------------------------


def check_links(vault: Vault) -> CheckResult:
    result = CheckResult("A", "链接")

    for basename, rels in sorted(vault.basename_index.items()):
        unique = sorted(set(rels))
        if len(unique) > 1:
            result.add_warning(
                "A6",
                f"文件名重复（全库唯一性）：{basename}：{', '.join(unique)}",
            )

    for rel, info in vault.files.items():
        if under_any(rel, vault.link_exempt):
            continue

        for heading in info.headings:
            if "|" in heading:
                result.add_warning(
                    "A5",
                    f"标题含裸 '|'，无法被章节链接指向：{heading}",
                    rel,
                )

        for target, anchor in vault.iter_links(info.linkbody):
            if not target:
                if anchor and not anchor.startswith("^"):
                    _check_anchor(vault, result, info, info, anchor)
                continue

            resolved, kind = vault.resolve(target, rel)
            if resolved:
                if kind == "half_path":
                    result.add_error(
                        "A3",
                        f"半截路径（缺顶层目录）：[[{target}]]",
                        rel,
                    )
                if resolved != rel:
                    info.outlinks.add(resolved)
                    vault.files[resolved].inlinks.add(rel)
                if anchor and not anchor.startswith("^"):
                    _check_anchor(vault, result, info, vault.files[resolved], anchor)
                continue

            if kind == "ambiguous":
                result.add_error(
                    "A2",
                    f"歧义链接（文件名重复，请写顶层全路径）：[[{target}]]",
                    rel,
                )
            elif kind == "half_path":
                result.add_error(
                    "A3",
                    f"半截路径（缺顶层目录）：[[{target}]]",
                    rel,
                )
            else:
                result.add_error("A1", f"断链：[[{target}]]", rel)

        for target, anchor in vault.iter_embeds(info.linkbody):
            if not target:
                continue
            suffix = posixpath.splitext(target)[1].lower()
            if suffix and suffix not in (".md", ".markdown"):
                # 附件嵌入不在主审计范围内；只检查笔记嵌入。
                continue
            resolved, kind = vault.resolve(target, rel)
            if not resolved:
                result.add_error("A7", f"嵌入目标不存在：![[{target}]]", rel)
                continue
            if kind == "half_path":
                result.add_error(
                    "A3",
                    f"半截路径（缺顶层目录）：![[{target}]]",
                    rel,
                )
            if resolved != rel:
                info.outlinks.add(resolved)
                vault.files[resolved].inlinks.add(rel)
            if anchor and not anchor.startswith("^"):
                _check_anchor(vault, result, info, vault.files[resolved], anchor)

    return result


def _check_anchor(
    vault: Vault,
    result: CheckResult,
    source: FileInfo,
    target: FileInfo,
    anchor: str,
) -> None:
    if normalize_heading(anchor) not in target.heading_norms:
        suffix = "" if source.rel == target.rel else f" -> {target.rel}"
        result.add_error(
            "A4",
            f"锚点失效：[[...{suffix}#{anchor}]]",
            source.rel,
        )


def check_frontmatter(vault: Vault) -> CheckResult:
    result = CheckResult("B", "frontmatter")
    config = vault.config

    type_vocab = set(config.get("type_vocab", []))
    status_vocab = set(config.get("status_vocab", []))
    source_vocab = set(config.get("source_type_vocab", []))
    required = list(config.get("required_fields", []))
    required_source_types = set(config.get("source_type_required_types", []))
    status_by_type = config.get("status_by_type", {})
    expected_by_dir = config.get("expected_types_by_dir", {})
    banned_tags = set(config.get("banned_tags", []))
    date_fields = list(config.get("date_fields", []))
    review_requires = bool(config.get("review_requires_evidence", False))
    form_vocab = set(config.get("form_vocab", []))
    fm_exempt = config.get("frontmatter_exempt_prefixes", [])
    fm_exempt_files = set(config.get("frontmatter_exempt_files", []))

    for rel, message in vault.read_errors:
        result.add_error("B0", f"无法按 UTF-8 读取：{message}", rel)

    alias_map: Dict[str, List[str]] = {}

    for rel, info in vault.files.items():
        if rel in fm_exempt_files or under_any(rel, fm_exempt):
            continue

        fm = info.fm
        if not fm:
            result.add_error("B1", "缺少 frontmatter", rel)
            continue

        missing = [name for name in required if is_empty(fm.get(name))]
        if missing:
            result.add_error("B1", "缺少必填字段：" + ", ".join(missing), rel)

        typ = fm.get("type", "")
        status = fm.get("status", "")
        typ_str = typ if isinstance(typ, str) else ""
        status_str = status if isinstance(status, str) else ""

        type_ok = typ_str in type_vocab
        status_ok = status_str in status_vocab

        if not type_ok:
            result.add_error("B3", f"非法 type：{typ_str!r}", rel)
        if not status_ok:
            result.add_error("B3", f"非法 status：{status_str!r}", rel)

        if type_ok and status_ok:
            allowed = status_by_type.get(typ_str)
            if allowed is not None and status_str not in allowed:
                result.add_error(
                    "B2",
                    f"status {status_str!r} 与 type {typ_str!r} 不兼容",
                    rel,
                )

        source_type = fm.get("source_type", "")
        source_str = source_type if isinstance(source_type, str) else ""
        if typ_str in required_source_types and not source_str:
            result.add_error("B4", "缺少 source_type", rel)
        elif source_str and source_str not in source_vocab:
            result.add_error("B4", f"非法 source_type：{source_str!r}", rel)

        form = fm.get("form", "")
        form_str = form if isinstance(form, str) else ""
        if form_str and form_vocab and form_str not in form_vocab:
            result.add_error("B10", f"非法 form：{form_str!r}", rel)

        directory = top_dir(rel)
        allowed_types = expected_by_dir.get(directory)
        if allowed_types is not None and type_ok and typ_str not in allowed_types:
            result.add_error(
                "B5",
                f"type {typ_str!r} 不应出现在 {directory!r}",
                rel,
            )

        if (
            review_requires
            and status_str == "需复习"
            and is_empty(fm.get("evidence_as_of"))
        ):
            result.add_error("B6", "status 为 需复习，但缺少 evidence_as_of", rel)

        tags = fm.get("tags", [])
        if isinstance(tags, str):
            tags = [tags] if tags else []
        if isinstance(tags, list):
            for tag in tags:
                if tag in banned_tags:
                    result.add_error("B7", f"使用了禁用标签：{tag}", rel)

        for field_name in date_fields:
            value = fm.get(field_name)
            if isinstance(value, str) and value and not is_date(value):
                result.add_error(
                    "B8",
                    f"{field_name} 不是合法日期（YYYY-MM-DD）：{value!r}",
                    rel,
                )

        aliases = fm.get("aliases", [])
        if isinstance(aliases, str):
            aliases = [aliases] if aliases else []
        if isinstance(aliases, list):
            for alias in aliases:
                if isinstance(alias, str) and alias.strip():
                    alias_map.setdefault(alias.strip(), []).append(rel)

    for alias, rels in sorted(alias_map.items()):
        unique = sorted(set(rels))
        if len(unique) > 1:
            result.add_warning(
                "B9",
                f"别名 {alias!r} 被多个文件使用：{', '.join(unique)}",
            )

    return result


def check_reachability(vault: Vault) -> CheckResult:
    result = CheckResult("C", "可达性")
    config = vault.config
    index_dir = config.get("index_dir", "00 索引")
    inactive = config.get("inactive_prefixes", [])

    seeds = [rel for rel in vault.files if top_dir(rel) == index_dir]
    seen: Set[str] = set(seeds)
    queue: List[str] = list(seeds)

    while queue:
        current = queue.pop()
        for target in vault.files[current].outlinks:
            if target not in seen:
                seen.add(target)
                queue.append(target)

    for rel, info in vault.files.items():
        if top_dir(rel) == "" or under_any(rel, inactive):
            continue
        if rel not in seen:
            result.add_warning("C1", "从 00 索引 不可达", rel)
        if rel not in seeds and not info.inlinks:
            result.add_warning("C2", "零入链（孤儿笔记）", rel)

    return result


def check_flow(vault: Vault) -> CheckResult:
    result = CheckResult("D", "消化链路")
    inactive = vault.config.get("inactive_prefixes", [])
    type_of = {rel: info.fm.get("type") for rel, info in vault.files.items()}

    reading = [
        rel
        for rel, typ in type_of.items()
        if typ == "reading" and not under_any(rel, inactive)
    ]
    topics = [
        rel
        for rel, typ in type_of.items()
        if typ == "topic" and not under_any(rel, inactive)
    ]
    evergreen = [
        rel
        for rel, typ in type_of.items()
        if typ == "evergreen" and not under_any(rel, inactive)
    ]

    cited_by_topic = {
        rel
        for rel in reading
        if any(type_of.get(src) == "topic" for src in vault.files[rel].inlinks)
    }
    cited_by_ever = {
        rel
        for rel in reading
        if any(type_of.get(src) == "evergreen" for src in vault.files[rel].inlinks)
    }
    topic_cites_ever = {
        rel
        for rel in topics
        if any(type_of.get(target) == "evergreen" for target in vault.files[rel].outlinks)
    }

    for rel in sorted(reading):
        if rel not in cited_by_topic and rel not in cited_by_ever:
            result.add_warning("D1", "02 阅读笔记未被任何 03/04 引用", rel)

    for rel in sorted(topics):
        if rel not in topic_cites_ever:
            result.add_warning("D2", "03 主题笔记未引用任何 04 常青卡", rel)

    vault.config["_flow_stats"] = {
        "reading": len(reading),
        "topic": len(topics),
        "evergreen": len(evergreen),
        "reading_cited_by_topic": len(cited_by_topic),
        "reading_cited_by_evergreen": len(cited_by_ever),
        "topic_citing_evergreen": len(topic_cites_ever),
    }
    return result


def check_stale(vault: Vault) -> CheckResult:
    result = CheckResult("E", "陈旧与复习")
    config = vault.config
    inactive = config.get("inactive_prefixes", [])
    stale_days = int(config.get("stale_days", 90))
    stale_exempt_tags = set(config.get("stale_exempt_tags", []))

    stale: List[Tuple[int, str]] = []
    for rel, info in vault.files.items():
        if top_dir(rel) == "" or under_any(rel, inactive):
            continue
        if info.fm.get("type") == "index":
            continue
        tags = info.fm.get("tags", [])
        if isinstance(tags, str):
            tags = [tags] if tags else []
        if isinstance(tags, list) and any(tag in stale_exempt_tags for tag in tags):
            continue
        age = days_since(info.fm.get("updated"))
        if age is not None and age > stale_days:
            stale.append((age, rel))

    if stale:
        stale.sort(reverse=True)
        preview = ", ".join(f"{rel}（{age} 天）" for age, rel in stale[:5])
        suffix = f" 等 {len(stale)} 篇" if len(stale) > 5 else ""
        result.add_warning(
            "E1",
            f"{len(stale)} 篇超过 {stale_days} 天未更新：{preview}{suffix}",
        )

    review = [
        rel
        for rel, info in vault.files.items()
        if info.fm.get("status") == "需复习" and not under_any(rel, inactive)
    ]
    overdue = []
    for rel in review:
        age = days_since(vault.files[rel].fm.get("evidence_as_of"))
        if age is not None and age > stale_days:
            overdue.append((age, rel))

    if overdue:
        overdue.sort(reverse=True)
        preview = ", ".join(f"{rel}（证据 {age} 天）" for age, rel in overdue[:5])
        suffix = f" 等 {len(overdue)} 篇" if len(overdue) > 5 else ""
        result.add_warning(
            "E2",
            f"{len(overdue)} 篇需复习笔记的证据已超过 {stale_days} 天：{preview}{suffix}",
        )

    return result


def check_placeholder(vault: Vault) -> CheckResult:
    result = CheckResult("F", "占位与空笔记")
    config = vault.config
    inactive = config.get("inactive_prefixes", [])
    exempt = config.get("placeholder_exempt_prefixes", [])
    empty_exempt = config.get("empty_exempt_prefixes", [])
    patterns = [re.compile(pattern) for pattern in config.get("placeholder_patterns", [])]
    min_lines = int(config.get("min_body_lines", 4))

    for rel, info in vault.files.items():
        if top_dir(rel) == "" or under_any(rel, inactive):
            continue

        if not under_any(rel, exempt):
            body = strip_comments(strip_inline_code(strip_fenced(info.body)))
            for pattern in patterns:
                match = pattern.search(body)
                if match:
                    result.add_warning(
                        "F1",
                        f"正文含占位内容：{match.group(0)!r}",
                        rel,
                    )
                    break

        if not under_any(rel, empty_exempt):
            lines = [line for line in info.body.splitlines() if line.strip()]
            if len(lines) < min_lines:
                result.add_warning(
                    "F2",
                    f"正文只有 {len(lines)} 行，疑似空桩",
                    rel,
                )

    return result


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------


REQUIRED_CONFIG_KEYS = [
    "top_dirs",
    "skip_dirs",
    "type_vocab",
    "status_vocab",
    "source_type_vocab",
    "required_fields",
    "status_by_type",
    "expected_types_by_dir",
    "banned_tags",
]


def load_config(path: Path) -> Dict[str, object]:
    try:
        with path.open(encoding="utf-8") as handle:
            config = json.load(handle)
    except FileNotFoundError as error:
        raise ConfigError(f"找不到配置文件：{path}") from error
    except json.JSONDecodeError as error:
        raise ConfigError(f"配置文件不是合法 JSON：{path}（{error}）") from error

    missing = [key for key in REQUIRED_CONFIG_KEYS if key not in config]
    if missing:
        raise ConfigError("配置缺少字段：" + ", ".join(missing))
    return config


def resolve_root(config_path: Path, config: Dict[str, object], override: Optional[str]) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    vault_root = config.get("vault_root", "..")
    root = Path(str(vault_root))
    if not root.is_absolute():
        root = config_path.parent / root
    return root.expanduser().resolve()


def run_audit(root: Path, config: Dict[str, object]) -> AuditReport:
    vault = Vault(root, config)
    checks = [
        check_links(vault),
        check_frontmatter(vault),
        check_reachability(vault),
        check_flow(vault),
        check_stale(vault),
        check_placeholder(vault),
    ]
    stats = {
        "notes": len(vault.files),
        "resolved_links": sum(len(info.outlinks) for info in vault.files.values()),
        "flow": config.get("_flow_stats", {}),
    }
    return AuditReport(root=str(root), checks=checks, stats=stats)


def print_report(report: AuditReport) -> None:
    print(f"知识库审计 · {report.root}")
    print("=" * 72)
    notes = report.stats.get("notes", 0)
    links = report.stats.get("resolved_links", 0)
    print(f"笔记 {notes} · 解析链接 {links}")
    flow = report.stats.get("flow") or {}
    if flow:
        print(
            "链路 "
            f"02 {flow.get('reading', 0)} / "
            f"03 {flow.get('topic', 0)} / "
            f"04 {flow.get('evergreen', 0)}"
        )
    print("-" * 72)
    for check in report.checks:
        status = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}[check.status]
        print(
            f"{check.id} {check.name:<10} {status:<5} "
            f"{len(check.errors)} errors, {len(check.warnings)} warnings"
        )
        for issue in check.errors + check.warnings:
            location = f"  → {issue.path}" if issue.path else ""
            print(f"  [{issue.code}] {issue.message}{location}")
    print("-" * 72)
    status = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}[report.status]
    print(f"结果：{status}（{report.errors} errors, {report.warnings} warnings）")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="知识库结构审计（只读）")
    parser.add_argument("--config", help="配置文件路径，默认 tools/kb_config.json")
    parser.add_argument("--root", help="知识库根目录，默认由配置的 vault_root 解析")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--strict", action="store_true", help="WARN 也返回非零退出码")
    args = parser.parse_args(argv)

    config_path = (
        Path(args.config).expanduser().resolve()
        if args.config
        else Path(__file__).resolve().parent / "kb_config.json"
    )

    try:
        config = load_config(config_path)
        root = resolve_root(config_path, config, args.root)
        if not root.is_dir():
            raise ConfigError(f"知识库根目录不存在：{root}")
        report = run_audit(root, config)
    except ConfigError as error:
        print(f"配置错误：{error}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print_report(report)

    if report.errors:
        return 1
    if args.strict and report.warnings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
