#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""删除示例内容并清理索引/导航（默认只预览）。

用法：
    python3 tools/kb_clean_demo.py
    python3 tools/kb_clean_demo.py --apply
    python3 tools/kb_clean_demo.py --root /path/to/vault --apply
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from kb_audit import ConfigError, load_config, resolve_root, run_audit


MANIFEST_PATH = Path(__file__).resolve().parent / "demo_manifest.json"


class CleanupError(Exception):
    """无法清理示例内容。"""


def load_manifest(path: Path = MANIFEST_PATH) -> Dict[str, object]:
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as error:
        raise CleanupError(f"找不到示例清单：{path}") from error
    except json.JSONDecodeError as error:
        raise CleanupError(f"示例清单不是合法 JSON：{path}（{error}）") from error
    if not isinstance(data, dict):
        raise CleanupError("示例清单必须是 JSON 对象。")
    for key in ("files", "directories", "keep_dirs", "line_filters"):
        if key in data and not isinstance(data[key], (list, dict)):
            raise CleanupError(f"示例清单字段 {key} 类型不对。")
    return data


def ensure_under_root(root: Path, rel: str) -> Path:
    path = (root / rel).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as error:
        raise CleanupError(f"清单路径越界：{rel}") from error
    return path


def strip_section(text: str, heading: str) -> Tuple[str, List[str]]:
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == heading), None)
    if start is None:
        return text, []
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")),
        len(lines),
    )
    removed = lines[start:end]
    new_lines = lines[:start] + lines[end:]
    while (
        0 < start < len(new_lines)
        and not new_lines[start - 1].strip()
        and not new_lines[start].strip()
    ):
        del new_lines[start]
    return "\n".join(new_lines).rstrip() + "\n", removed


def collect_plan(root: Path, manifest: Dict[str, object]) -> Dict[str, object]:
    root = root.resolve()
    files: List[Path] = []
    for rel in manifest.get("files", []):
        path = ensure_under_root(root, str(rel))
        if path.is_file():
            files.append(path)

    dirs: List[Path] = []
    for rel in manifest.get("directories", []):
        path = ensure_under_root(root, str(rel))
        if path.is_dir():
            dirs.append(path)

    edits: List[Dict[str, object]] = []
    line_filters = manifest.get("line_filters") or {}
    for rel, patterns in line_filters.items():
        path = ensure_under_root(root, str(rel))
        if not path.is_file():
            continue
        patterns = [str(pattern) for pattern in patterns]
        lines = path.read_text(encoding="utf-8").splitlines()
        kept = [line for line in lines if not any(pattern in line for pattern in patterns)]
        removed = [line for line in lines if any(pattern in line for pattern in patterns)]
        if removed:
            edits.append({"path": path, "kept": kept, "removed": removed})

    readme_path = root / "README.md"
    readme_text = ""
    readme_removed_lines: List[str] = []
    readme_removed_section: List[str] = []
    if readme_path.is_file():
        readme_text = readme_path.read_text(encoding="utf-8")
        for pattern in manifest.get("readme_line_filters", []):
            lines = readme_text.splitlines()
            kept = [line for line in lines if str(pattern) not in line]
            removed = [line for line in lines if str(pattern) in line]
            readme_removed_lines.extend(removed)
            readme_text = "\n".join(kept)
            if readme_text:
                readme_text += "\n"
        section = manifest.get("readme_section")
        if section:
            readme_text, readme_removed_section = strip_section(
                readme_text, str(section)
            )
        readme_text = re.sub(r"\n{3,}", "\n\n", readme_text).rstrip() + "\n"

    return {
        "files": files,
        "dirs": dirs,
        "edits": edits,
        "readme_path": readme_path,
        "readme_text": readme_text,
        "readme_removed_lines": readme_removed_lines,
        "readme_removed_section": readme_removed_section,
    }


def backup_paths(root: Path, paths: Iterable[Path]) -> Path:
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_root = root / ".backup" / f"demo-clean-{stamp}"
    backup_root.mkdir(parents=True, exist_ok=True)
    seen = set()
    for path in paths:
        if not path.exists():
            continue
        rel = path.relative_to(root)
        if rel in seen:
            continue
        seen.add(rel)
        dest = backup_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if path.is_dir():
            shutil.copytree(path, dest)
        else:
            shutil.copy2(path, dest)
    return backup_root


def clean(
    root: Path,
    config: Dict[str, object],
    manifest: Dict[str, object],
    apply: bool = False,
) -> int:
    root = root.resolve()
    plan = collect_plan(root, manifest)
    files: List[Path] = plan["files"]  # type: ignore[assignment]
    dirs: List[Path] = plan["dirs"]  # type: ignore[assignment]
    edits: List[Dict[str, object]] = plan["edits"]  # type: ignore[assignment]
    readme_path: Path = plan["readme_path"]  # type: ignore[assignment]
    readme_text: str = plan["readme_text"]  # type: ignore[assignment]
    readme_changed = (
        readme_path.is_file()
        and readme_text != readme_path.read_text(encoding="utf-8")
    )

    total = len(files) + len(dirs) + len(edits) + (1 if readme_changed else 0)
    if total == 0:
        print("没有找到需要清理的示例内容。")
        return 0

    print(f"将删除 {len(files)} 个文件、{len(dirs)} 个目录")
    for path in files:
        print(f"  - {path.relative_to(root).as_posix()}")
    for path in dirs:
        print(f"  - {path.relative_to(root).as_posix()}/")
    if edits:
        print(f"将清理 {len(edits)} 个索引/说明文件：")
        for edit in edits:
            path = edit["path"]
            removed = edit["removed"]
            print(f"  - {path.relative_to(root).as_posix()}（{len(removed)} 行）")
    if readme_changed:
        removed_count = len(plan["readme_removed_lines"]) + len(
            plan["readme_removed_section"]
        )
        print(f"将清理 README.md 的示例段（{removed_count} 行）")

    if not apply:
        print("（dry-run；加 --apply 才会写入，写入前自动备份到 .backup/）")
        return 0

    affected = list(files) + list(dirs) + [edit["path"] for edit in edits]
    if readme_changed:
        affected.append(readme_path)
    backup_root = backup_paths(root, affected)
    print(f"已备份：{backup_root.relative_to(root).as_posix()}")

    for path in files:
        path.unlink()
    for path in dirs:
        shutil.rmtree(path)
    for edit in edits:
        path = edit["path"]
        kept = edit["kept"]
        path.write_text("\n".join(kept).rstrip() + "\n", encoding="utf-8")
    if readme_changed:
        readme_path.write_text(readme_text, encoding="utf-8")

    for rel in manifest.get("keep_dirs", []):
        path = ensure_under_root(root, str(rel))
        if path.is_dir() and not any(path.iterdir()):
            (path / ".gitkeep").write_text("", encoding="utf-8")

    report = run_audit(root, config)
    print(
        f"清理完成；审计 {report.status.upper()} "
        f"（{report.errors} errors, {report.warnings} warnings）"
    )
    for check in report.checks:
        for issue in check.errors + check.warnings:
            location = f" → {issue.path}" if issue.path else ""
            print(f"  [{issue.code}] {issue.message}{location}")
    return 0 if not report.errors else 1


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="删除 starter 自带的示例内容（默认只预览）")
    parser.add_argument("--apply", action="store_true", help="真正写入；默认 dry-run")
    parser.add_argument("--manifest", help="示例清单路径，默认 tools/demo_manifest.json")
    parser.add_argument("--config", help="配置文件路径，默认 tools/kb_config.json")
    parser.add_argument("--root", help="知识库根目录，默认由配置的 vault_root 解析")
    args = parser.parse_args(argv)

    config_path = (
        Path(args.config).expanduser().resolve()
        if args.config
        else Path(__file__).resolve().parent / "kb_config.json"
    )
    manifest_path = (
        Path(args.manifest).expanduser().resolve()
        if args.manifest
        else MANIFEST_PATH
    )

    try:
        config = load_config(config_path)
        root = resolve_root(config_path, config, args.root)
        if not root.is_dir():
            raise CleanupError(f"知识库根目录不存在：{root}")
        manifest = load_manifest(manifest_path)
        return clean(root, config, manifest, apply=args.apply)
    except (ConfigError, CleanupError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
