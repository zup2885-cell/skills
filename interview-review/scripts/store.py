#!/usr/bin/env python3
"""Local, evidence-checked interview records and rebuildable Markdown views."""

import argparse
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from contextlib import contextmanager
from datetime import date, datetime, timezone


DEFAULT_ROOT = Path.home() / "Documents" / "面试经验库"
KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}\Z")
STATUSES = {"strong": "证据充分", "partial": "仍有缺口", "gap": "关键缺口", "unknown": "未观察/证据不足"}
OUTCOMES = {"pending": "待结果", "advanced": "进入下一轮", "rejected": "未通过", "offered": "收到录用", "withdrawn": "主动退出", "unknown": "未知"}
KINDS = {"transcript": "逐字稿", "recall": "用户回忆", "notes": "局部笔记"}
MANAGED = {"created_at", "updated_at", "source_sha256"}


class StoreError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise StoreError(message)


def string(value, label, empty=False):
    require(isinstance(value, str) and (empty or bool(value.strip())), f"{label} 须为{'可空' if empty else '非空'}字符串")


def key(value, label):
    require(isinstance(value, str) and KEY.fullmatch(value), f"{label} 格式无效")


def strings(value, label):
    require(isinstance(value, list), f"{label} 须为列表")
    for item in value:
        string(item, label)


def validate(record):
    require(isinstance(record, dict), "记录须为 JSON 对象")
    require(type(record.get("schema_version")) is int and record["schema_version"] == 1, "schema_version 须为 1")
    key(record.get("session_id"), "session_id")
    require("interview_date" in record, "缺少 interview_date")
    if record["interview_date"] is not None:
        value = record["interview_date"]
        require(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value), "interview_date 须为 YYYY-MM-DD 或 null")
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise StoreError("interview_date 不是有效日期") from exc
    for field in ("company", "role", "round"):
        require(field in record, f"缺少 {field}")
        if record[field] is not None:
            string(record[field], field)
    require(record.get("outcome") in OUTCOMES, "outcome 无效")
    string(record.get("summary"), "summary")
    source = record.get("source")
    require(isinstance(source, dict), "缺少 source")
    require(source.get("kind") in KINDS, "source.kind 无效")
    string(source.get("name"), "source.name")
    string(source.get("text"), "source.text")
    lines = source["text"].splitlines()
    questions = record.get("questions")
    require(isinstance(questions, list) and questions, "questions 至少含一题")
    ids = set()
    for q in questions:
        require(isinstance(q, dict), "question 须为对象")
        key(q.get("id"), "question.id")
        require(q["id"] not in ids, "同场 question.id 重复")
        ids.add(q["id"])
        key(q.get("topic_key"), "topic_key")
        for field in ("question", "answer", "better_answer"):
            string(q.get(field), field)
        require(q.get("status") in STATUSES, "question.status 无效")
        for field in ("worked", "gap_tags", "missing"):
            strings(q.get(field), field)
        evidence = q.get("evidence")
        require(isinstance(evidence, list) and evidence, f"{q['id']} 缺少 evidence")
        for ref in evidence:
            require(isinstance(ref, dict), "evidence 须为对象")
            require(ref.get("speaker", "unknown") in ("interviewer", "candidate", "unknown"), "evidence.speaker 无效")
            start, end = ref.get("start_line"), ref.get("end_line")
            require(type(start) is int and type(end) is int and 1 <= start <= end <= len(lines), "引用行号越界或格式无效")
            require(ref.get("quote") == "\n".join(lines[start - 1:end]), f"{q['id']} 引用与原文不一致")
    stories = record.get("stories")
    require(isinstance(stories, list), "stories 须为列表")
    story_keys = set()
    for story in stories:
        require(isinstance(story, dict), "story 须为对象")
        key(story.get("key"), "story.key")
        require(story["key"] not in story_keys, "同场 story.key 重复")
        story_keys.add(story["key"])
        for field in ("title", "text"):
            string(story.get(field), "story." + field)
        refs = story.get("question_ids")
        require(isinstance(refs, list) and refs, "story 须引用本场题号")
        require(all(isinstance(ref, str) and ref in ids for ref in refs), "story 引用不存在的题号")
    strings(record.get("next_actions"), "next_actions")
    require(len(record["next_actions"]) <= 3, "next_actions 最多三项")
    return record


def source_hash(record):
    return hashlib.sha256(record["source"]["text"].strip().encode("utf-8")).hexdigest()


def user_content(record):
    return {k: v for k, v in record.items() if k not in MANAGED}


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise StoreError(f"无法读取 JSON：{path}（{exc}）") from exc


def safe_root(root):
    root = Path(root).expanduser().resolve()
    for parent in (root, *root.parents):
        require(not (parent / ".git").exists() and not (parent / ".hg").exists(), "真实面试经验库不能放在 Git/Hg 仓库内，请换到 Documents 下的独立目录")
    skill = Path(__file__).resolve().parents[1]
    require(root != skill and skill not in root.parents and root not in skill.parents, "经验库不能与 Skill 源码目录重叠")
    for name in ("records", "reviews", "history", "drafts", ".store.lock"):
        require(not (root / name).is_symlink(), f"经验库中的 {name} 不得为符号链接")
    return root


@contextmanager
def locked(root):
    root = safe_root(root)
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".store.lock").open("a", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        for name in ("records", "reviews", "history", "drafts"):
            (root / name).mkdir(exist_ok=True)
        try:
            yield root
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def load_records(root):
    records = []
    hashes = set()
    for path in sorted((root / "records").glob("*.json")):
        try:
            record = validate(read_json(path))
            require(path.stem == record["session_id"], "文件名与 session_id 不一致")
            fingerprint = source_hash(record)
            require(record.get("source_sha256") == fingerprint, "source_sha256 与原文不一致")
            require(fingerprint not in hashes, "多条记录含相同来源全文")
            hashes.add(fingerprint)
            records.append(record)
        except StoreError as exc:
            raise StoreError(f"{path}：{exc}") from exc
    return sorted(records, key=lambda r: (r["interview_date"] or "", r["session_id"]))


def escape(text):
    # Keep source text literal when embedded in Markdown; never render raw HTML.
    text = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"([\\`*_{}\[\]#|!])", r"\\\1", text)


def label(record):
    return escape(" / ".join([record["interview_date"] or "日期待补", record["company"] or "公司待补", record["role"] or "岗位待补", record["round"] or "轮次待补"]))


def report_link(record):
    return f"[{label(record)}](reviews/{record['session_id']}.md)"


def quoted_refs(refs):
    result = []
    for ref in sorted(refs, key=lambda item: item["start_line"]):
        result += [f"L{ref['start_line']}—L{ref['end_line']}：", "", *["> " + escape(line) for line in ref["quote"].splitlines()], ""]
    return result


def report(record):
    result = [f"# {label(record)}", "", escape(record["summary"]), "", f"结果：{OUTCOMES[record['outcome']]}；来源：{KINDS[record['source']['kind']]} / {escape(record['source']['name'])}", "", f"[完整原记录](../records/{record['session_id']}.json)", ""]
    for q in record["questions"]:
        interviewer = [ref for ref in q["evidence"] if ref.get("speaker") == "interviewer"]
        candidate = [ref for ref in q["evidence"] if ref.get("speaker") == "candidate"]
        unknown = [ref for ref in q["evidence"] if ref.get("speaker", "unknown") == "unknown"]
        result += [f"## {q['id']} · {escape(q['question'])}", "", "### 1. 面试官怎么问", ""]
        result += quoted_refs(interviewer) if interviewer else [escape(q["question"]), "", "以上为整理后的问题；未标注面试官原话。", ""]
        result += ["### 2. 你当时怎么答", ""]
        if candidate:
            if record["source"]["kind"] == "recall":
                result += ["以下来自用户回忆，不是录音逐字稿。", ""]
            result += quoted_refs(candidate) + ["回答摘要：" + escape(q["answer"]), ""]
        else:
            result += [escape(q["answer"]), "", "以上为回答摘要；未标注候选人原话，不能当作逐字引用。", ""]
        result += ["### 3. 问题在哪", "", "答得好的地方：" + ("；".join(escape(x) for x in q["worked"]) or "暂无足够证据"), "", "具体问题与原因：" + ("；".join(escape(x) for x in q["missing"]) or "暂无明确缺口"), "", f"本次证据状态：{STATUSES[q['status']]}", "", "### 4. 下次怎么答", "", escape(q["better_answer"]), ""]
        if unknown:
            result += ["补充依据（角色未标注或未确认）：", ""] + quoted_refs(unknown)
    result += ["## 下一场动作", ""] + [f"{i}. {escape(action)}" for i, action in enumerate(record["next_actions"], 1)]
    if not record["next_actions"]:
        result += ["暂无动作；待补材料后确定。"]
    return "\n".join(result).rstrip() + "\n"


def render(records):
    views = {f"reviews/{r['session_id']}.md": report(r) for r in records}
    index = ["# 面试复盘入口", "", "## 开始一场复盘", "", "在当前 Codex 聊天里点击「开始面试复盘」，再把面试录音拖入聊天。也可以直接发本机录音文件的完整路径。支持 M4A、MP3、WAV；已有文字记录也可以直接粘贴。", "", "收到材料后，逐题给你看：面试官怎么问 → 你当时怎么答 → 具体问题在哪 → 下次怎么答。听不清或说话人不确定的位置会标出来。", "", "也可以在聊天里直接说：用面试逐题复盘分析这份录音。", "", "## 已保存的复盘", "", f"共 {len(records)} 场。日期待补的记录不用于前后趋势判断。", "", "[问题库](question-bank.md) · [回答库](answer-bank.md) · [下场准备](next-interview.md)", ""]
    index += [f"- {report_link(r)} — {OUTCOMES[r['outcome']]}" for r in records]
    index[2:2] = ["[打开电脑端面试复盘工作台](http://127.0.0.1:18761)", "", "若页面打不开，双击本机“面试复盘.command”或项目里的“启动面试复盘.command”启动。工作台可按场次查看原问、原答、具体问题和完整改答。", ""]
    if not records:
        index += ["尚无真实面试记录。可以提供逐字稿、笔记或口述回忆开始。"]
    views["index.md"] = "\n".join(index) + "\n"
    topics = {}
    for r in records:
        for q in r["questions"]:
            topics.setdefault(q["topic_key"], []).append((r, q))
    bank = ["# 问题库", "", "次数按不同场次计；多场缺口只是线索，须回到原话人工复核。", ""]
    for topic, entries in sorted(topics.items()):
        counts = {}
        for r, q in entries:
            if q["status"] in ("gap", "partial"):
                for tag in set(q["gap_tags"]):
                    counts.setdefault(tag, set()).add(r["session_id"])
        bank += [f"## {topic}", "", f"出现于 {len({r['session_id'] for r, _ in entries})} 场。", ""]
        for tag, sessions in sorted(counts.items()):
            if len(sessions) >= 2:
                bank += [f"- 多场缺口线索：{escape(tag)}，涉及 {len(sessions)} 场。"]
        bank += [f"- {report_link(r)} / {q['id']}：{escape(q['question'])} — {STATUSES[q['status']]}；缺口标签：{escape('、'.join(q['gap_tags'])) or '无'}" for r, q in entries]
        bank += [""]
    views["question-bank.md"] = "\n".join(bank) + "\n"
    answers = ["# 回答与案例库", "", "按来源保留各版答法。方括号内待补项尚未确认，不能当作已做经历。", ""]
    for topic, entries in sorted(topics.items()):
        answers += [f"## {topic}", ""]
        for r, q in entries:
            answers += [f"### {label(r)} / {q['id']}", "", escape(q["better_answer"]), "", report_link(r), ""]
    answers += ["## 个人案例草稿", ""]
    for r in records:
        for story in r["stories"]:
            answers += [f"### {escape(story['title'])}", "", escape(story["text"]), "", f"来源：{report_link(r)} / {', '.join(story['question_ids'])}；案例键：{story['key']}", ""]
    views["answer-bank.md"] = "\n".join(answers) + "\n"
    actions = ["# 下场准备素材", "", "尚未指定下一场岗位时，仅作通用准备。由 Agent 结合 JD、近期关键缺口和成本，从下列素材挑最多 3 项；这里不自动判定问题已解决。", ""]
    for r in reversed(records):
        actions += [f"## {label(r)}", "", report_link(r), ""]
        actions += [f"- {escape(action)}" for action in r["next_actions"]] + [""]
    views["next-interview.md"] = "\n".join(actions) + "\n"
    return views


def rebuild(root, records):
    views = render(records)
    for relative, content in views.items():
        atomic_write(root / relative, content)
    return views


def save(root, record, revise=False):
    record = copy.deepcopy(user_content(record))
    validate(record)
    records = load_records(root)
    current = next((r for r in records if r["session_id"] == record["session_id"]), None)
    fingerprint = source_hash(record)
    require(not any(r["session_id"] != record["session_id"] and source_hash(r) == fingerprint for r in records), "来源全文已存在于另一场记录，请核对 session_id")
    if current and user_content(current) == record:
        rebuild(root, records)
        return "unchanged"
    require(not current or revise, "同 session_id 内容有变化；用户要求补充、纠错或回填后才能用 --revise")
    now = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    record.update(created_at=current["created_at"] if current else now, updated_at=now, source_sha256=fingerprint)
    if current:
        archive = root / "history" / record["session_id"] / (now.replace(":", "-") + ".json")
        atomic_write(archive, json_text(current))
    atomic_write(root / "records" / (record["session_id"] + ".json"), json_text(record))
    # If a derived write fails, canonical JSON remains and rebuild can recover it.
    rebuild(root, load_records(root))
    return "revised" if current else "created"


def check(root):
    records = load_records(root)
    for relative, expected in render(records).items():
        path = root / relative
        require(path.is_file() and path.read_text(encoding="utf-8") == expected, f"派生文件缺失或过期：{path}；运行 rebuild")
    expected_reviews = {r["session_id"] for r in records}
    require({p.stem for p in (root / "reviews").glob("*.md")} == expected_reviews, "reviews 含无对应记录的文件，请人工核对")
    return len(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("init", "save", "rebuild", "check"))
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--input", type=Path)
    parser.add_argument("--revise", action="store_true")
    args = parser.parse_args()
    try:
        require(args.command == "save" or not args.revise, "--revise 只用于 save")
        incoming = None
        if args.command == "save":
            require(args.input is not None, "save 需要 --input")
            incoming = validate(read_json(args.input))
        with locked(args.root) as root:
            if args.command == "save":
                status = save(root, incoming, args.revise)
            elif args.command == "check":
                status = "checked"
            else:
                rebuild(root, load_records(root))
                status = "initialized" if args.command == "init" else "rebuilt"
            count = check(root)
            print(json.dumps({"status": status, "sessions": count, "root": str(root)}, ensure_ascii=False))
        return 0
    except (StoreError, OSError, KeyError, TypeError) as exc:
        print(f"失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
