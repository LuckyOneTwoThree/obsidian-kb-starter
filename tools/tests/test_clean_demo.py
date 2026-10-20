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

        report = self.audit()
        self.assertEqual(report.errors, 0, report.to_dict())
        self.assertEqual(report.warnings, 0, report.to_dict())

        # 再跑一次应当是空操作
        again = kb_clean_demo.clean(
            self.root, copy.deepcopy(BASE_CONFIG), self.manifest, apply=True
        )
        self.assertEqual(again, 0)


if __name__ == "__main__":
    unittest.main()
