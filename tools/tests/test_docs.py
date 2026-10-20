#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""仓库文档自检：本地 Markdown 链接 + 示例清单覆盖。"""

from __future__ import annotations

import json
import re
import sys
import unittest
import urllib.parse
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
VAULT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

import kb_audit  # noqa: E402
import kb_clean_demo  # noqa: E402


with (TOOLS / "kb_config.json").open(encoding="utf-8") as _handle:
    BASE_CONFIG = json.load(_handle)


MD_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
SKIP_PARTS = {".git", ".obsidian", ".backup", "__pycache__", "tools"}


class DocsTests(unittest.TestCase):
    def iter_markdown(self):
        for path in VAULT.rglob("*.md"):
            if any(part in SKIP_PARTS for part in path.parts):
                continue
            yield path

    def test_local_markdown_links_exist(self):
        missing = []
        for path in self.iter_markdown():
            text = path.read_text(encoding="utf-8")
            text = kb_audit.make_linkable(
                text, BASE_CONFIG.get("ignore_line_prefixes", [])
            )
            for match in MD_LINK_RE.finditer(text):
                target = match.group(1).strip()
                if target.startswith("<") and target.endswith(">"):
                    target = target[1:-1]
                target = urllib.parse.unquote(target)
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                target = target.split("#", 1)[0]
                if not target:
                    continue
                candidate = (path.parent / target).resolve()
                if not candidate.exists():
                    missing.append(
                        f"{path.relative_to(VAULT).as_posix()} -> {target}"
                    )
        self.assertEqual(missing, [], "\n".join(missing))

    def test_demo_manifest_covers_tagged_notes(self):
        guide = VAULT / "00 索引/示例导览.md"
        if not guide.is_file():
            self.skipTest("demo content already cleaned")
        manifest = kb_clean_demo.load_manifest()
        manifest_paths = {
            str(item["path"]) for item in manifest.get("files", [])
        }

        for item in manifest.get("files", []):
            rel = str(item["path"])
            path = VAULT / rel
            self.assertTrue(path.is_file(), f"manifest 文件不存在：{rel}")
            text = path.read_text(encoding="utf-8")
            mode = str(item["verify"])
            if mode == "marker":
                self.assertIn("示例内容", text, rel)
            elif mode == "tag":
                fm, _ = kb_audit.parse_frontmatter(text)
                tags = fm.get("tags", [])
                if isinstance(tags, str):
                    tags = [tags] if tags else []
                self.assertIn("示例", tags, f"缺少示例标签：{rel}")
            elif mode == "none":
                continue
            else:
                self.fail(f"未知 verify：{mode}")

        for path in self.iter_markdown():
            text = path.read_text(encoding="utf-8")
            fm, _ = kb_audit.parse_frontmatter(text)
            tags = fm.get("tags", [])
            if isinstance(tags, str):
                tags = [tags] if tags else []
            if isinstance(tags, list) and "示例" in tags:
                rel = path.relative_to(VAULT).as_posix()
                self.assertIn(
                    rel, manifest_paths, f"示例笔记未加入 demo_manifest：{rel}"
                )


if __name__ == "__main__":
    unittest.main()
