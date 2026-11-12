"""Synthetic data only. Run: python3 -B -m unittest discover -s scripts -v"""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import store


def sample(session="demo-a", day="2026-11-01", status="partial", topic="content-ops.project-ownership"):
    source = f"虚构演示 {session}\n面试官：你负责什么，如何验证效果？\n我：我负责脚本和剪辑，没有整理结果。"
    return {
        "schema_version": 1, "session_id": session, "interview_date": day,
        "company": "虚构公司", "role": "内容运营", "round": "一面", "outcome": "pending",
        "summary": "职责清楚，结果依据待补。", "source": {"kind": "recall", "name": "虚构测试", "text": source},
        "questions": [{"id": "Q1", "topic_key": topic, "question": "项目职责与验证方式？",
                       "answer": "负责脚本和剪辑，未说明结果依据。", "status": status,
                       "worked": ["职责具体"], "gap_tags": ["结果证据"], "missing": ["缺结果依据"],
                       "better_answer": "我负责脚本和剪辑。[待补：真实验证依据]",
                       "evidence": [{"start_line": 3, "end_line": 3, "quote": source.splitlines()[2]}]}],
        "stories": [{"key": "editing-project", "title": "脚本剪辑案例", "text": "负责脚本和剪辑；结果待补。", "question_ids": ["Q1"]}],
        "next_actions": ["找出真实结果记录；找不到就说明已有验证范围。"],
    }


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="interview-review-test-")
        self.root = Path(self.temp.name) / "private"
        self.addCleanup(self.temp.cleanup)

    def put(self, record, revise=False):
        with store.locked(self.root) as root:
            return store.save(root, record, revise)

    def test_empty_init_then_three_sessions_preserve_history(self):
        with store.locked(self.root) as root:
            store.rebuild(root, [])
            self.assertEqual(store.check(root), 0)
        self.put(sample())
        self.put(sample("demo-b", "2026-11-03", "gap"))
        third = sample("demo-c", "2026-11-05", "strong")
        third["source"]["text"] = "虚构第三场\n面试官：如何验证效果？\n我：我交付前后各统计了一周完播率，记录在同一张表里。"
        third["questions"][0].update(answer="说明了前后各一周的比较和同表记录。", gap_tags=[], missing=[],
                                      better_answer="我用交付前后各一周的完播率做比较，记录在同一张表里。")
        third["questions"][0]["evidence"][0]["quote"] = third["source"]["text"].splitlines()[2]
        third["stories"] = []
        self.put(third)
        self.assertEqual(store.check(self.root), 3)
        bank = (self.root / "question-bank.md").read_text()
        self.assertIn("出现于 3 场", bank)
        self.assertIn("结果证据，涉及 2 场", bank)
        self.assertIn("证据充分", bank)
        self.assertIn("仍有缺口", bank)
        self.assertNotIn("已解决", bank)
        self.assertIn("待补", (self.root / "answer-bank.md").read_text())

    def test_same_round_followups_count_once(self):
        record = sample()
        another = copy.deepcopy(record["questions"][0])
        another["id"] = "Q2"
        record["questions"].append(another)
        self.put(record)
        bank = (self.root / "question-bank.md").read_text()
        self.assertIn("出现于 1 场", bank)
        self.assertNotIn("多场缺口线索：", bank)

    def test_reimport_is_idempotent(self):
        record = sample()
        self.assertEqual(self.put(record), "created")
        first = (self.root / "records/demo-a.json").read_bytes()
        self.assertEqual(self.put(record), "unchanged")
        self.assertEqual(first, (self.root / "records/demo-a.json").read_bytes())
        self.assertEqual(store.check(self.root), 1)

    def test_revision_requires_flag_and_preserves_old_record(self):
        record = sample()
        self.put(record)
        record["outcome"] = "advanced"
        with self.assertRaises(store.StoreError):
            self.put(record)
        self.assertEqual(self.put(record, revise=True), "revised")
        history = list((self.root / "history/demo-a").glob("*.json"))
        self.assertEqual(len(history), 1)
        self.assertEqual(json.loads(history[0].read_text())["outcome"], "pending")
        self.assertEqual(store.check(self.root), 1)
        self.assertIn("进入下一轮", (self.root / "index.md").read_text())

    def test_same_source_new_id_rejected(self):
        record = sample()
        self.put(record)
        record["session_id"] = "different-id"
        with self.assertRaisesRegex(store.StoreError, "另一场"):
            self.put(record)
        self.assertEqual(store.check(self.root), 1)

    def test_invalid_evidence_never_creates_record(self):
        record = sample()
        record["questions"][0]["evidence"][0]["quote"] = "我提升了 300%（这是编造，必须拒绝）"
        with self.assertRaisesRegex(store.StoreError, "原文不一致"):
            self.put(record)
        self.assertEqual(list((self.root / "records").glob("*.json")), [])

    def test_bad_line_ranges(self):
        for start, end in [(0, 1), (1, 4), (3, 2), (True, 1)]:
            with self.subTest(start=start, end=end):
                record = sample()
                record["questions"][0]["evidence"][0].update(start_line=start, end_line=end)
                with self.assertRaises(store.StoreError):
                    store.validate(record)

    def test_dates_and_unsafe_ids(self):
        for value in ["2026-02-29", "2026-13-01", "2026-1-1", 123]:
            record = sample(day=value)
            with self.subTest(value=value), self.assertRaises(store.StoreError):
                store.validate(record)
        self.assertIsNotNone(store.validate(sample(day=None)))
        for value in ["../escape", "/tmp/x", "x/y", "..", "a" * 101]:
            record = sample(session=value)
            with self.subTest(value=value), self.assertRaises(store.StoreError):
                store.validate(record)

    def test_unknown_is_not_counted_as_gap(self):
        self.put(sample())
        self.put(sample("demo-b", status="unknown"))
        bank = (self.root / "question-bank.md").read_text()
        self.assertNotIn("多场缺口线索：", bank)
        self.assertIn("未观察/证据不足", bank)

    def test_different_role_topics_not_merged(self):
        self.put(sample())
        record = sample("demo-b", topic="sales.project-ownership")
        record["role"] = "销售"
        self.put(record)
        bank = (self.root / "question-bank.md").read_text()
        self.assertEqual(bank.count("出现于 1 场"), 2)

    def test_rebuild_repairs_modified_view(self):
        self.put(sample())
        (self.root / "question-bank.md").write_text("错误摘要")
        with self.assertRaisesRegex(store.StoreError, "过期"):
            store.check(self.root)
        store.rebuild(self.root, store.load_records(self.root))
        self.assertEqual(store.check(self.root), 1)

    def test_write_failure_preserves_canonical_for_recovery(self):
        with patch.object(store, "rebuild", side_effect=OSError("simulated disk error")):
            with self.assertRaises(OSError):
                self.put(sample())
        self.assertTrue((self.root / "records/demo-a.json").exists())
        store.rebuild(self.root, store.load_records(self.root))
        self.assertEqual(store.check(self.root), 1)

    def test_git_repository_refused(self):
        self.root.mkdir(parents=True)
        (self.root / ".git").write_text("gitdir: /not-used")
        with self.assertRaisesRegex(store.StoreError, "Git/Hg"):
            store.safe_root(self.root / "private")

    def test_bad_story_and_duplicate_question_id(self):
        record = sample()
        record["stories"][0]["question_ids"] = ["Q999"]
        with self.assertRaises(store.StoreError):
            store.validate(record)
        record = sample()
        record["questions"].append(copy.deepcopy(record["questions"][0]))
        with self.assertRaises(store.StoreError):
            store.validate(record)

    def test_two_concurrent_cli_saves_keep_both_sessions(self):
        processes = []
        for session in ("demo-a", "demo-b"):
            path = Path(self.temp.name) / (session + ".json")
            path.write_text(json.dumps(sample(session)), encoding="utf-8")
            processes.append(subprocess.Popen([sys.executable, "-B", store.__file__, "save", "--input", str(path), "--root", str(self.root)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
        for proc in processes:
            out, err = proc.communicate(timeout=15)
            self.assertEqual(proc.returncode, 0, err + out)
        self.assertEqual(store.check(self.root), 2)

    def test_raw_html_is_escaped_in_views(self):
        record = sample()
        record["summary"] = '<script>alert("synthetic")</script>'
        self.put(record)
        report = (self.root / "reviews/demo-a.md").read_text()
        self.assertNotIn("<script>", report)
        self.assertIn("&lt;script&gt;", report)

    def test_corrupt_record_is_reported_without_overwrite(self):
        self.put(sample())
        path = self.root / "records/demo-a.json"
        original = path.read_text()
        path.write_text("{broken", encoding="utf-8")
        with self.assertRaisesRegex(store.StoreError, "demo-a.json"):
            store.load_records(self.root)
        self.assertEqual(path.read_text(), "{broken")
        path.write_text(original, encoding="utf-8")
        self.assertEqual(store.check(self.root), 1)


if __name__ == "__main__":
    unittest.main()
