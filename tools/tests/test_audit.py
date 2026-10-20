#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kb_audit / kb_new 的最小单元测试。

运行：
    python3 -m unittest discover -s tools/tests -v
"""

from __future__ import annotations

import contextlib
import copy
import datetime as dt
import io
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
import kb_new  # noqa: E402


with (TOOLS / "kb_config.json").open(encoding="utf-8") as _handle:
    BASE_CONFIG = json.load(_handle)


class VaultTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # -- helpers ---------------------------------------------------------
    def write(self, rel: str, text: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def note(
        self,
        rel: str,
        type_: str,
        status: str,
        source_type: str = "",
        body: str = "正文内容。\n\n## 小节\n\n内容。\n",
        tags=None,
        aliases=None,
        created: str = "2026-10-01",
        updated: str = "2026-10-01",
        extra: str = "",
    ) -> Path:
        lines = ["---", f"type: {type_}", f"status: {status}"]
        if source_type:
            lines.append(f"source_type: {source_type}")
        if tags:
            lines.append("tags: [" + ", ".join(tags) + "]")
        else:
            lines.append("tags: []")
        if aliases:
            lines.append("aliases:")
            for alias in aliases:
                lines.append(f"  - {alias}")
        lines.extend([f"created: {created}", f"updated: {updated}"])
        if extra:
            lines.extend(extra.rstrip().splitlines())
        lines.extend(["---", "", "# 测试", "", body])
        return self.write(rel, "\n".join(lines))

    def home(self, links=None, body: str = "") -> Path:
        lines = ["# 首页", ""]
        for link in links or []:
            lines.append(f"- [[{link}]]")
        if body:
            lines.extend(["", body])
        return self.note(
            "00 索引/主页.md",
            "index",
            "active",
            body="\n".join(lines) + "\n",
        )

    def audit(self):
        return kb_audit.run_audit(self.root, copy.deepcopy(BASE_CONFIG))

    def assert_code(self, report, code: str):
        self.assertTrue(report.by_code(code), f"expected {code}, got {report.to_dict()}")


class LinkTests(VaultTestCase):
    def test_clean_link(self):
        self.home(["笔记"])
        self.note("02 阅读笔记/B 文章/笔记.md", "reading", "待阅读", "文章")
        report = self.audit()
        self.assertEqual(report.errors, 0, report.to_dict())

    def test_broken_link(self):
        self.home(["不存在"])
        report = self.audit()
        self.assert_code(report, "A1")

    def test_ambiguous_basename(self):
        self.home(["同名"])
        self.note("02 阅读笔记/B 文章/同名.md", "reading", "待阅读", "文章")
        self.note("03 主题笔记/A 工作/同名.md", "topic", "待提炼", "阅读笔记")
        report = self.audit()
        self.assert_code(report, "A2")

    def test_full_path_resolves_duplicate(self):
        self.home(["02 阅读笔记/B 文章/同名"])
        self.note("02 阅读笔记/B 文章/同名.md", "reading", "待阅读", "文章")
        self.note("03 主题笔记/A 工作/同名.md", "topic", "待提炼", "阅读笔记")
        report = self.audit()
        self.assertFalse(report.by_code("A2"), report.to_dict())

    def test_half_path(self):
        self.home(["B 文章/只有一篇"])
        self.note("02 阅读笔记/B 文章/只有一篇.md", "reading", "待阅读", "文章")
        report = self.audit()
        self.assert_code(report, "A3")

    def test_table_escaped_alias(self):
        self.home(body="| 链接 |\n|---|\n| [[测试笔记\\|别名]] |")
        self.note("02 阅读笔记/B 文章/测试笔记.md", "reading", "待阅读", "文章")
        report = self.audit()
        self.assertFalse(report.by_code("A1"), report.to_dict())
        self.assertFalse(report.by_code("A2"), report.to_dict())

    def test_fenced_code_ignored(self):
        self.home(body="```\n[[不存在]]\n```")
        report = self.audit()
        self.assertFalse(report.by_code("A1"), report.to_dict())

    def test_inline_code_ignored(self):
        self.home(body="`[[不存在]]`")
        report = self.audit()
        self.assertFalse(report.by_code("A1"), report.to_dict())

    def test_counter_example_line_ignored(self):
        self.home(body="❌ [[不存在]]")
        report = self.audit()
        self.assertFalse(report.by_code("A1"), report.to_dict())

    def test_anchor_normalization(self):
        self.home(["笔记", "笔记#8 与经典方法论的映射"])
        self.note(
            "02 阅读笔记/B 文章/笔记.md",
            "reading",
            "待阅读",
            "文章",
            body="## 8️⃣ 与经典方法论的映射\n\n内容。\n\n补充。\n",
        )
        report = self.audit()
        self.assertFalse(report.by_code("A4"), report.to_dict())

    def test_broken_anchor(self):
        self.home(["笔记", "笔记#不存在的标题"])
        self.note("02 阅读笔记/B 文章/笔记.md", "reading", "待阅读", "文章")
        report = self.audit()
        self.assert_code(report, "A4")

    def test_bare_pipe_heading_warns(self):
        self.home(["笔记"])
        self.note(
            "02 阅读笔记/B 文章/笔记.md",
            "reading",
            "待阅读",
            "文章",
            body="## A | B\n\n内容。\n",
        )
        report = self.audit()
        self.assert_code(report, "A5")

    def test_alias_resolution(self):
        self.home(["旧名字"])
        self.note(
            "02 阅读笔记/B 文章/新名字.md",
            "reading",
            "待阅读",
            "文章",
            aliases=["旧名字"],
        )
        report = self.audit()
        self.assertFalse(report.by_code("A1"), report.to_dict())

    def test_duplicate_basename_warns(self):
        self.home(["02 阅读笔记/B 文章/同名"])
        self.note("02 阅读笔记/B 文章/同名.md", "reading", "待阅读", "文章")
        self.note("03 主题笔记/A 工作/同名.md", "topic", "待提炼", "阅读笔记")
        report = self.audit()
        self.assert_code(report, "A6")

    def test_case_only_duplicate_basename_warns(self):
        self.home(["02 阅读笔记/B 文章/Foo"])
        self.note("02 阅读笔记/B 文章/Foo.md", "reading", "待阅读", "文章")
        self.note("03 主题笔记/A 工作/foo.md", "topic", "待提炼", "阅读笔记")
        report = self.audit()
        self.assert_code(report, "A6")

    def test_embed_missing_note(self):
        self.home(body="![[不存在]]")
        report = self.audit()
        self.assert_code(report, "A7")

    def test_embed_attachment_ignored(self):
        self.home(body="![[图片.png]]")
        report = self.audit()
        self.assertFalse(report.by_code("A7"), report.to_dict())

    def test_embed_note_resolves(self):
        self.home(body="![[笔记]]")
        self.note("02 阅读笔记/B 文章/笔记.md", "reading", "待阅读", "文章")
        report = self.audit()
        self.assertFalse(report.by_code("A7"), report.to_dict())

    def test_embed_broken_anchor(self):
        self.home(body="![[笔记#不存在的标题]]")
        self.note("02 阅读笔记/B 文章/笔记.md", "reading", "待阅读", "文章")
        report = self.audit()
        self.assert_code(report, "A4")

    def test_setext_heading_anchor(self):
        self.home(["笔记#Setext 标题"])
        self.note(
            "02 阅读笔记/B 文章/笔记.md",
            "reading",
            "待阅读",
            "文章",
            body="Setext 标题\n==========\n\n正文内容。\n\n补充。\n",
        )
        report = self.audit()
        self.assertFalse(report.by_code("A4"), report.to_dict())

    def test_heading_in_html_comment_is_ignored(self):
        self.home(["笔记#Hidden"])
        self.note(
            "02 阅读笔记/B 文章/笔记.md",
            "reading",
            "待阅读",
            "文章",
            body="<!--\n## Hidden\n-->\n\n正文内容。\n\n补充。\n",
        )
        report = self.audit()
        self.assert_code(report, "A4")

    def test_case_insensitive_link_warns_a8(self):
        self.home(["case"])
        self.note("02 阅读笔记/B 文章/Case.md", "reading", "待阅读", "文章")
        report = self.audit()
        self.assert_code(report, "A8")
        self.assertFalse(report.by_code("A1"), report.to_dict())

    def test_alias_vs_basename_collision_warns_b15(self):
        self.home(["Foo"])
        self.note("02 阅读笔记/B 文章/Foo.md", "reading", "待阅读", "文章")
        self.note(
            "03 主题笔记/A 工作/别名.md",
            "topic",
            "待提炼",
            "阅读笔记",
            aliases=["Foo"],
        )
        report = self.audit()
        self.assert_code(report, "B15")


class FrontmatterTests(VaultTestCase):
    def test_illegal_status_for_type(self):
        self.home(["笔记"])
        self.note("03 主题笔记/A 工作/笔记.md", "topic", "已沉淀", "阅读笔记")
        report = self.audit()
        self.assert_code(report, "B2")

    def test_illegal_status_value(self):
        self.home(["笔记"])
        self.note("03 主题笔记/A 工作/笔记.md", "topic", "乱写", "阅读笔记")
        report = self.audit()
        self.assert_code(report, "B3")

    def test_missing_source_type(self):
        self.home(["笔记"])
        self.note("02 阅读笔记/B 文章/笔记.md", "reading", "待阅读")
        report = self.audit()
        self.assert_code(report, "B4")

    def test_type_directory_mismatch(self):
        self.home(["笔记"])
        self.note("02 阅读笔记/B 文章/笔记.md", "topic", "待提炼", "阅读笔记")
        report = self.audit()
        self.assert_code(report, "B5")

    def test_review_requires_evidence(self):
        self.home(["笔记"])
        self.note("02 阅读笔记/B 文章/笔记.md", "reading", "需复习", "文章")
        report = self.audit()
        self.assert_code(report, "B6")

    def test_banned_tag(self):
        self.home(["笔记"])
        self.note(
            "02 阅读笔记/B 文章/笔记.md",
            "reading",
            "待阅读",
            "文章",
            tags=["项目"],
        )
        report = self.audit()
        self.assert_code(report, "B7")

    def test_invalid_date(self):
        self.home(["笔记"])
        self.note(
            "02 阅读笔记/B 文章/笔记.md",
            "reading",
            "待阅读",
            "文章",
            created="2026/10/01",
        )
        report = self.audit()
        self.assert_code(report, "B8")

    def test_inbox_without_frontmatter_is_allowed(self):
        self.write("01 收件箱/A 临时想法/2026-10-01.md", "# 日记\n\n一句话。\n")
        report = self.audit()
        self.assertFalse(report.by_code("B1"), report.to_dict())

    def test_template_folder_is_exempt(self):
        self.write(
            "07 资料库/D 模板/_模板_测试.md",
            "---\ntype: reading\nstatus: {{status}}\n---\n\n# 模板\n\n[[ ]]\n",
        )
        report = self.audit()
        self.assertFalse(report.by_code("B1"), report.to_dict())
        self.assertFalse(report.by_code("B3"), report.to_dict())
        self.assertFalse(report.by_code("A1"), report.to_dict())

    def test_invalid_form(self):
        self.home(["笔记"])
        self.note(
            "04 常青笔记/E 判断/笔记.md",
            "evergreen",
            "草稿",
            "阅读笔记",
            extra="form: 隨筆",
        )
        report = self.audit()
        self.assert_code(report, "B10")

    def test_bom_frontmatter(self):
        self.write(
            "02 阅读笔记/B 文章/带BOM.md",
            "\ufeff---\ntype: reading\nstatus: 待阅读\n"
            "source_type: 文章\ntags: []\n"
            "created: 2026-10-01\nupdated: 2026-10-01\n---\n\n"
            "# 测试\n\n正文。\n",
        )
        self.home(["带BOM"])
        report = self.audit()
        self.assertFalse(report.by_code("B1"), report.to_dict())

    def test_non_utf8_reports_b0(self):
        path = self.root / "02 阅读笔记/B 文章/坏编码.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"---\ntype: reading\nstatus: \x81\x82\n---\n")
        report = self.audit()
        self.assert_code(report, "B0")

    def test_repo_doc_without_frontmatter_is_exempt(self):
        self.write("CHANGELOG.md", "# Changelog\n\n- item\n")
        report = self.audit()
        self.assertFalse(report.by_code("B1"), report.to_dict())

    def test_layout_mismatch_warns(self):
        self.home(["阅读", "主题", "卡片"])
        self.note(
            "02 阅读笔记/B 文章/阅读.md",
            "reading",
            "待阅读",
            "书籍",
        )
        self.note(
            "03 主题笔记/A 工作/主题.md",
            "topic",
            "待提炼",
            "阅读笔记",
            extra="area: 学习",
        )
        self.note(
            "04 常青笔记/E 判断/卡片.md",
            "evergreen",
            "草稿",
            "阅读笔记",
            extra="form: 方法",
        )
        report = self.audit()
        self.assertEqual(len(report.by_code("B11")), 3, report.to_dict())

    def test_evergreen_missing_form_warns(self):
        self.home(["卡片"])
        self.note(
            "04 常青笔记/E 判断/卡片.md",
            "evergreen",
            "草稿",
            "阅读笔记",
        )
        report = self.audit()
        self.assert_code(report, "B12")

    def test_project_path_and_doc_path_warn(self):
        self.home(["松散项目", "other"])
        self.note(
            "05 项目/松散项目.md",
            "project",
            "待启动",
            "原创随笔",
        )
        self.note(
            "05 项目/2026/2026-x/other.md",
            "project_doc",
            "草稿",
        )
        report = self.audit()
        self.assertEqual(len(report.by_code("B13")), 2, report.to_dict())

    def test_archived_project_outside_archive_warns(self):
        self.home(["已归档项目-项目主页"])
        self.note(
            "05 项目/2026/2026-已归档项目/2026-已归档项目-项目主页.md",
            "project",
            "已归档",
            "原创随笔",
        )
        report = self.audit()
        self.assert_code(report, "B14")


class ReachabilityAndQualityTests(VaultTestCase):
    def test_unreachable_note(self):
        self.home([])
        self.note("02 阅读笔记/B 文章/孤岛.md", "reading", "待阅读", "文章")
        report = self.audit()
        self.assert_code(report, "C1")

    def test_orphan_note(self):
        self.home([])
        self.note("02 阅读笔记/B 文章/孤岛.md", "reading", "待阅读", "文章")
        report = self.audit()
        self.assert_code(report, "C2")

    def test_placeholder(self):
        self.home(["笔记"])
        self.note(
            "02 阅读笔记/B 文章/笔记.md",
            "reading",
            "待阅读",
            "文章",
            body="TODO 补充\n\n## 小节\n\n内容。\n",
        )
        report = self.audit()
        self.assert_code(report, "F1")

    def test_empty_note(self):
        self.home(["笔记"])
        self.note(
            "02 阅读笔记/B 文章/笔记.md",
            "reading",
            "待阅读",
            "文章",
            body="短句。\n",
        )
        report = self.audit()
        self.assert_code(report, "F2")

    def test_flow_gap_warns(self):
        self.home(["阅读笔记"])
        self.note(
            "02 阅读笔记/B 文章/阅读笔记.md",
            "reading",
            "已沉淀",
            "文章",
        )
        report = self.audit()
        self.assert_code(report, "D1")

    def test_stale_demo_tag_exempt(self):
        self.home(["笔记"])
        self.note(
            "02 阅读笔记/B 文章/笔记.md",
            "reading",
            "已沉淀",
            "文章",
            tags=["示例"],
            updated="2020-01-01",
        )
        report = self.audit()
        self.assertFalse(report.by_code("E1"), report.to_dict())

    def test_stale_without_demo_tag_warns(self):
        self.home(["笔记"])
        self.note(
            "02 阅读笔记/B 文章/笔记.md",
            "reading",
            "已沉淀",
            "文章",
            updated="2020-01-01",
        )
        report = self.audit()
        self.assert_code(report, "E1")

    def test_completed_project_without_review_warns(self):
        self.home(["2026-项目-项目主页"])
        self.note(
            "05 项目/2026/2026-项目/2026-项目-项目主页.md",
            "project",
            "已完成",
            "原创随笔",
        )
        report = self.audit()
        self.assert_code(report, "C3")

    def test_completed_project_with_review_does_not_warn(self):
        self.home(["2026-项目-项目主页", "复盘"])
        self.note(
            "05 项目/2026/2026-项目/2026-项目-项目主页.md",
            "project",
            "已完成",
            "原创随笔",
            body="正文内容。\n\n## 复盘\n\n- [[复盘]]\n\n补充。\n",
        )
        self.note(
            "03 主题笔记/A 工作/复盘.md",
            "review",
            "已完成",
        )
        report = self.audit()
        self.assertFalse(report.by_code("C3"), report.to_dict())

    def test_active_project_stale_warns_e3(self):
        self.home(["2026-项目-项目主页"])
        self.note(
            "05 项目/2026/2026-项目/2026-项目-项目主页.md",
            "project",
            "进行中",
            "原创随笔",
            updated="2020-01-01",
        )
        report = self.audit()
        self.assert_code(report, "E3")

    def test_active_project_with_demo_tag_is_exempt(self):
        self.home(["2026-项目-项目主页"])
        self.note(
            "05 项目/2026/2026-项目/2026-项目-项目主页.md",
            "project",
            "进行中",
            "原创随笔",
            tags=["示例"],
            updated="2020-01-01",
        )
        report = self.audit()
        self.assertFalse(report.by_code("E3"), report.to_dict())

    def test_inbox_aging_warns_e4(self):
        self.home([])
        self.write(
            "01 收件箱/A 临时想法/2020-01-01.md",
            "# 2020-01-01\n\n- 一条旧捕获。\n",
        )
        report = self.audit()
        self.assert_code(report, "E4")

    def test_inbox_demo_marker_is_exempt(self):
        self.home([])
        self.write(
            "01 收件箱/A 临时想法/2020-01-01.md",
            "<!-- 示例内容，可删除 -->\n# 2020-01-01\n\n- 示例捕获。\n",
        )
        report = self.audit()
        self.assertFalse(report.by_code("E4"), report.to_dict())

    def test_summary_output_groups_by_code(self):
        self.home(["笔记"])
        self.note("02 阅读笔记/B 文章/笔记.md", "reading", "待阅读", "文章")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = kb_audit.main(["--root", str(self.root), "--summary"])
        output = stdout.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("[D1] 1 条", output)


class NewNoteTests(unittest.TestCase):
    def test_sanitize_filename(self):
        self.assertEqual(kb_new.sanitize_filename("a/b|c"), "a-b-c")

    def test_sanitize_md_suffix_and_control_chars(self):
        self.assertEqual(kb_new.sanitize_filename("foo.md"), "foo")
        self.assertEqual(kb_new.sanitize_filename("foo.md.md"), "foo")
        self.assertEqual(kb_new.sanitize_filename("a\x00b"), "a-b")
        with self.assertRaises(kb_new.NewNoteError):
            kb_new.sanitize_filename(".md")

    def test_sanitize_windows_reserved_names(self):
        for title in ("CON", "con", "PRN", "LPT1", "COM9"):
            with self.assertRaises(kb_new.NewNoteError):
                kb_new.sanitize_filename(title)

    def test_validate_target_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = copy.deepcopy(BASE_CONFIG)
            valid = [
                ("02 阅读笔记/B 文章/x.md", "reading"),
                ("03 主题笔记/A 工作/x.md", "topic"),
                ("04 常青笔记/E 判断/x.md", "evergreen"),
                ("05 项目/2026/2026-x/2026-x-项目主页.md", "project"),
                ("01 收件箱/A 临时想法/2026-10-12.md", "daily"),
            ]
            for rel, kind in valid:
                kb_new.validate_target_dir(root, config, Path(rel), kind)

            invalid = [
                ("99 归档/x.md", "reading"),
                ("00 索引/x.md", "reading"),
                ("07 资料库/x.md", "reading"),
                (".obsidian/x.md", "reading"),
                ("01 收件箱/D/x.md", "reading"),
                ("05 项目/2026/custom/2026-x-项目主页.md", "project"),
                ("05 项目/2026/2026-x/项目主页.md", "project"),
            ]
            for rel, kind in invalid:
                with self.assertRaises(kb_new.NewNoteError):
                    kb_new.validate_target_dir(root, config, Path(rel), kind)

    def test_validate_target_dir_rejects_symlink_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "vault"
            outside = base / "outside"
            (root / "02 阅读笔记/B 文章").mkdir(parents=True)
            outside.mkdir()
            try:
                (root / "02 阅读笔记/B 文章/evil").symlink_to(
                    outside, target_is_directory=True
                )
            except OSError as error:
                self.skipTest(f"symlink not available: {error}")
            with self.assertRaises(kb_new.NewNoteError):
                kb_new.validate_target_dir(
                    root,
                    copy.deepcopy(BASE_CONFIG),
                    Path("02 阅读笔记/B 文章/evil/x.md"),
                    "reading",
                )

    def test_destination_project_avoids_double_year(self):
        rel, title = kb_new.destination(
            "project",
            "2026-周报改造",
            dt.date(2026, 10, 20),
            2026,
            "",
            "原创随笔",
            "",
            None,
        )
        self.assertEqual(title, "周报改造")
        self.assertEqual(
            rel.as_posix(),
            "05 项目/2026/2026-周报改造/2026-周报改造-项目主页.md",
        )

    def test_set_field_replaces_empty_value(self):
        text = "---\ntype: topic\narea:\n---\n"
        updated = kb_new.set_field(text, "area", "工作")
        self.assertEqual(updated.count("area:"), 1)
        self.assertIn("area: 工作", updated)

    def test_render_project(self):
        template = (VAULT / "07 资料库/D 模板/_模板_项目主页.md").read_text(
            encoding="utf-8"
        )
        text = kb_new.render_template(
            template,
            "project",
            "2026-周报改造",
            dt.date(2026, 10, 20),
            2026,
            "",
            "原创随笔",
            "",
            None,
            copy.deepcopy(BASE_CONFIG),
        )
        self.assertIn("type: project", text)
        self.assertIn("# 2026-周报改造", text)
        self.assertNotIn("{{", text)

    def test_render_reading(self):
        template = (VAULT / "07 资料库/D 模板/_模板_阅读笔记.md").read_text(
            encoding="utf-8"
        )
        text = kb_new.render_template(
            template,
            "reading",
            "测试文章",
            dt.date(2026, 10, 20),
            2026,
            "工作",
            "文章",
            "",
            None,
            copy.deepcopy(BASE_CONFIG),
        )
        self.assertIn("type: reading", text)
        self.assertIn("status: 待阅读", text)
        self.assertIn("source_type: 文章", text)
        self.assertNotIn("{{", text)

    def test_render_evergreen_form(self):
        template = (VAULT / "07 资料库/D 模板/_模板_常青卡.md").read_text(
            encoding="utf-8"
        )
        text = kb_new.render_template(
            template,
            "evergreen",
            "测试判断",
            dt.date(2026, 10, 20),
            2026,
            "工作",
            "阅读笔记",
            "判断",
            None,
            copy.deepcopy(BASE_CONFIG),
        )
        self.assertIn("form: 判断", text)
        self.assertIn("status: 草稿", text)

    def test_render_rejects_bad_status(self):
        template = (VAULT / "07 资料库/D 模板/_模板_阅读笔记.md").read_text(
            encoding="utf-8"
        )
        with self.assertRaises(kb_new.NewNoteError):
            kb_new.render_template(
                template,
                "reading",
                "测试",
                dt.date(2026, 10, 20),
                2026,
                "工作",
                "文章",
                "",
                "已提炼",
                copy.deepcopy(BASE_CONFIG),
            )

    def test_render_time_and_custom_date(self):
        template = (
            "---\ntype: reading\nstatus: 待阅读\n"
            "created: {{date:YYYY-MM-DD}} {{time}}\n"
            "updated: {{date}}\n---\n\n# {{title}}\n"
        )
        text = kb_new.render_template(
            template,
            "reading",
            "测试",
            dt.date(2026, 10, 20),
            2026,
            "",
            "文章",
            "",
            None,
            copy.deepcopy(BASE_CONFIG),
        )
        self.assertNotIn("{{", text)
        self.assertIn("2026-10-20", text)

    def test_find_name_conflicts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "02 阅读笔记/B 文章/同名.md"
            path.parent.mkdir(parents=True)
            path.write_text(
                "---\ntype: reading\nstatus: 待阅读\nsource_type: 文章\n"
                "tags: []\ncreated: 2026-10-01\nupdated: 2026-10-01\n---\n\n"
                "# 同名\n\n正文\n",
                encoding="utf-8",
            )
            conflicts = kb_new.find_name_conflicts(
                root,
                copy.deepcopy(BASE_CONFIG),
                Path("03 主题笔记/A 工作/同名.md"),
            )
            self.assertEqual(conflicts, ["02 阅读笔记/B 文章/同名.md"])

    def test_find_alias_conflicts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "02 阅读笔记/B 文章/新名字.md"
            path.parent.mkdir(parents=True)
            path.write_text(
                "---\ntype: reading\nstatus: 待阅读\nsource_type: 文章\n"
                "tags: []\naliases:\n  - 旧名字\n"
                "created: 2026-10-01\nupdated: 2026-10-01\n---\n\n"
                "# 新名字\n\n正文\n",
                encoding="utf-8",
            )
            conflicts = kb_new.find_name_conflicts(
                root,
                copy.deepcopy(BASE_CONFIG),
                Path("03 主题笔记/A 工作/旧名字.md"),
            )
            self.assertEqual(conflicts, ["02 阅读笔记/B 文章/新名字.md"])

    def test_find_case_only_conflicts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "02 阅读笔记/B 文章/Foo.md"
            path.parent.mkdir(parents=True)
            path.write_text(
                "---\ntype: reading\nstatus: 待阅读\nsource_type: 文章\n"
                "tags: []\ncreated: 2026-10-01\nupdated: 2026-10-01\n---\n\n"
                "# Foo\n\n正文\n",
                encoding="utf-8",
            )
            conflicts = kb_new.find_name_conflicts(
                root,
                copy.deepcopy(BASE_CONFIG),
                Path("03 主题笔记/A 工作/foo.md"),
            )
            self.assertEqual(conflicts, ["02 阅读笔记/B 文章/Foo.md"])

    def test_backup_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rel = Path("01 收件箱/A 临时想法/旧.md")
            target = root / rel
            target.parent.mkdir(parents=True)
            target.write_text("旧内容", encoding="utf-8")
            backup = kb_new.backup_existing(root, rel)
            self.assertTrue(backup.is_file())
            self.assertEqual(backup.read_text(encoding="utf-8"), "旧内容")

    def test_cli_rejects_duplicate_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            shutil.copytree(
                VAULT,
                root,
                ignore=shutil.ignore_patterns(
                    ".git", ".obsidian", "__pycache__", ".backup"
                ),
            )
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = kb_new.main(
                    [
                        "evergreen",
                        "--title",
                        "示例-决策日志的最小字段",
                        "--form",
                        "判断",
                        "--root",
                        str(root),
                    ]
                )
            self.assertEqual(code, 2)
            self.assertIn("文件名已存在", stderr.getvalue())

    def test_cli_force_creates_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            shutil.copytree(
                VAULT,
                root,
                ignore=shutil.ignore_patterns(
                    ".git", ".obsidian", "__pycache__", ".backup"
                ),
            )
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = kb_new.main(
                    [
                        "daily",
                        "--date",
                        "2026-10-12",
                        "--force",
                        "--root",
                        str(root),
                    ]
                )
            self.assertEqual(code, 0, stderr.getvalue())
            backups = list((root / ".backup").glob("kb_new-*/**/2026-10-12.md"))
            self.assertTrue(backups, list((root / ".backup").rglob("*")))

    def test_cli_rejects_bad_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            shutil.copytree(
                VAULT,
                root,
                ignore=shutil.ignore_patterns(
                    ".git", ".obsidian", "__pycache__", ".backup"
                ),
            )
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = kb_new.main(
                    [
                        "reading",
                        "--title",
                        "不该创建",
                        "--dir",
                        "99 归档",
                        "--root",
                        str(root),
                    ]
                )
            self.assertEqual(code, 2)
            self.assertIn("99 归档", stderr.getvalue())
            self.assertFalse((root / "99 归档/不该创建.md").exists())


if __name__ == "__main__":
    unittest.main()
