#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""示例清理脚本的集成测试。"""

from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
VAULT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

import kb_audit  # noqa: E402
import kb_clean_demo  # noqa: E402


with (TOOLS / "kb_config.json").open(encoding="utf-8") as _handle:
    BASE_CONFIG = json.load(_handle)


class CleanDemoTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "vault"
        shutil.copytree(
            VAULT,
            self.root,
            ignore=shutil.ignore_patterns(
                ".git", ".obsidian", "__pycache__", ".backup"
            ),
        )
        self.manifest = kb_clean_demo.load_manifest()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def audit(self):
        return kb_audit.run_audit(self.root, copy.deepcopy(BASE_CONFIG))

    def test_dry_run_does_not_modify(self):
        demo = self.root / "01 收件箱/A 临时想法/2026-10-12.md"
        self.assertTrue(demo.is_file())
        result = kb_clean_demo.clean(
            self.root, copy.deepcopy(BASE_CONFIG), self.manifest, apply=False
        )
        self.assertEqual(result, 0)
        self.assertTrue(demo.is_file())
        self.assertFalse((self.root / ".backup").exists())

    def test_apply_removes_demo_and_audit_passes(self):
        result = kb_clean_demo.clean(
            self.root, copy.deepcopy(BASE_CONFIG), self.manifest, apply=True
        )
        self.assertEqual(result, 0)

        self.assertFalse(
            (self.root / "01 收件箱/A 临时想法/2026-10-12.md").exists()
        )
        self.assertFalse((self.root / "00 索引/示例导览.md").exists())
        self.assertFalse((self.root / "05 项目/2026/2026-周报改造").exists())
        self.assertTrue((self.root / "01 收件箱/A 临时想法/.gitkeep").is_file())
        self.assertNotIn(
            "示例导览",
            (self.root / "README.md").read_text(encoding="utf-8"),
        )

        report = self.audit()
        self.assertEqual(report.errors, 0, report.to_dict())
        self.assertEqual(report.warnings, 0, report.to_dict())

        # 再跑一次应当是空操作
        again = kb_clean_demo.clean(
            self.root, copy.deepcopy(BASE_CONFIG), self.manifest, apply=True
        )
        self.assertEqual(again, 0)

    def test_user_file_in_demo_project_is_preserved(self):
        project = self.root / "05 项目/2026/2026-周报改造"
        user_file = project / "我的真实笔记.txt"
        user_file.write_text("个人内容", encoding="utf-8")

        result = kb_clean_demo.clean(
            self.root, copy.deepcopy(BASE_CONFIG), self.manifest, apply=True
        )
        self.assertEqual(result, 0)
        self.assertTrue(user_file.is_file())
        self.assertTrue(project.is_dir())
        self.assertFalse((project / "2026-周报改造-项目主页.md").exists())
        self.assertFalse((project / "2026-周报改造-方案.md").exists())

        report = self.audit()
        self.assertEqual(report.errors, 0, report.to_dict())
        self.assertEqual(report.warnings, 0, report.to_dict())

    def test_untagged_demo_is_skipped_unless_forced(self):
        card = (
            self.root
            / "04 常青笔记/D 方法/示例-决策日志的最小字段.md"
        )
        text = card.read_text(encoding="utf-8")
        card.write_text(text.replace("  - 示例\n", ""), encoding="utf-8")

        result = kb_clean_demo.clean(
            self.root, copy.deepcopy(BASE_CONFIG), self.manifest, apply=True
        )
        # 被跳过的示例仍引用已删除文件，审计应返回非零提醒。
        self.assertEqual(result, 1)
        self.assertTrue(card.is_file())

        forced = kb_clean_demo.clean(
            self.root,
            copy.deepcopy(BASE_CONFIG),
            self.manifest,
            apply=True,
            force=True,
        )
        self.assertEqual(forced, 0)
        self.assertFalse(card.exists())

    def test_daily_sample_requires_marker(self):
        daily = self.root / "01 收件箱/A 临时想法/2026-10-12.md"
        text = daily.read_text(encoding="utf-8")
        daily.write_text(text.replace("示例内容", "普通内容"), encoding="utf-8")

        result = kb_clean_demo.clean(
            self.root, copy.deepcopy(BASE_CONFIG), self.manifest, apply=True
        )
        self.assertEqual(result, 0)
        self.assertTrue(daily.is_file())

        forced = kb_clean_demo.clean(
            self.root,
            copy.deepcopy(BASE_CONFIG),
            self.manifest,
            apply=True,
            force=True,
        )
        self.assertEqual(forced, 0)
        self.assertFalse(daily.exists())

    def test_manifest_path_traversal_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["files"] = [{"path": "../outside.md", "verify": "none"}]
        with self.assertRaises(kb_clean_demo.CleanupError):
            kb_clean_demo.clean(
                self.root, copy.deepcopy(BASE_CONFIG), manifest, apply=False
            )

    def test_backup_contains_deleted_file(self):
        result = kb_clean_demo.clean(
            self.root, copy.deepcopy(BASE_CONFIG), self.manifest, apply=True
        )
        self.assertEqual(result, 0)
        backups = list((self.root / ".backup").glob("demo-clean-*"))
        self.assertTrue(backups)
        backed_up = (
            backups[0]
            / "02 阅读笔记/B 文章/示例-远程团队为什么需要写决策日志.md"
        )
        self.assertTrue(backed_up.is_file())


if __name__ == "__main__":
    unittest.main()
