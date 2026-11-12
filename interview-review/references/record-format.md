# 记录格式与本地命令

需要 Python 3.9+，只用标准库。下方 `SKILL_DIR` 指当前 `SKILL.md` 所在的实际目录，不要把路径当成相对工作目录。

```bash
SKILL_DIR='/Users/m3air/GitHub/skills/interview-review'
python3 "$SKILL_DIR/scripts/store.py" init
python3 "$SKILL_DIR/scripts/store.py" save --input "$HOME/Documents/面试经验库/drafts/session.json"
python3 "$SKILL_DIR/scripts/store.py" check
python3 "$SKILL_DIR/scripts/store.py" rebuild
```

默认经验库 `~/Documents/面试经验库`。每条命令可追加 `--root '/其他绝对路径'`，且后续命令都沿用该值。不要把用户指定路径直接拼成可执行 shell 代码。

只有用户要求补充、纠错或回填某一场时：

```bash
python3 "$SKILL_DIR/scripts/store.py" save --input '/经验库/drafts/session.json' --revise
```

改前读取原 `records/<session_id>.json`，补充后仍保留原 source.text；若新增了回忆、材料或反馈，追加至 source.text 并标注来源，不篡改原话，检查新行号。旧 JSON 自动存入 `history/`。同一 JSON 重复保存不增加场次；不同 session_id 下完全相同的 source.text 会拒绝，先核对是否是同一面试。

## JSON 数据契约

下面全部是虚构演示，不是用户经历。source.text 中的“行”按换行计数。未知字段用 null 或空列表，不能补造。

```json
{
  "schema_version": 1,
  "session_id": "demo-a-round1",
  "interview_date": null,
  "company": "虚构甲公司",
  "role": "内容运营",
  "round": "一面",
  "outcome": "pending",
  "summary": "职责说清了，结果证据还缺。",
  "source": {
    "kind": "recall",
    "name": "用户口述回忆，虚构示例",
    "text": "面试官：这个项目你负责什么？\n我：我负责脚本和剪辑。\n面试官：怎么判断效果？\n我：当时没有记下结果。"
  },
  "questions": [
    {
      "id": "Q1",
      "topic_key": "content-ops.project-ownership",
      "question": "这个项目你负责什么？怎么判断效果？（合并整理）",
      "answer": "负责脚本和剪辑，没有提供结果。",
      "status": "partial",
      "worked": ["说明了自己的两个职责"],
      "gap_tags": ["结果证据"],
      "missing": ["没有说明效果如何验证"],
      "better_answer": "我负责脚本和剪辑。[待补：效果的实际验证依据]",
      "evidence": [
        {"speaker": "interviewer", "start_line": 1, "end_line": 1, "quote": "面试官：这个项目你负责什么？"},
        {"speaker": "candidate", "start_line": 2, "end_line": 2, "quote": "我：我负责脚本和剪辑。"},
        {"speaker": "interviewer", "start_line": 3, "end_line": 3, "quote": "面试官：怎么判断效果？"},
        {"speaker": "candidate", "start_line": 4, "end_line": 4, "quote": "我：当时没有记下结果。"}
      ]
    }
  ],
  "stories": [
    {
      "key": "script-editing-project",
      "title": "脚本与剪辑项目（待补证据）",
      "text": "我负责脚本和剪辑。[待补：背景、行动与效果依据]",
      "question_ids": ["Q1"]
    }
  ],
  "next_actions": ["找出该项目的真实结果记录；找不到则明确说明已有验证范围。"]
}
```

必需字段如上。interview_date 是真实面试日期 `YYYY-MM-DD` 或 null；outcome 仅为 `pending`、`advanced`、`rejected`、`offered`、`withdrawn`、`unknown`。source.kind 仅为 `transcript`、`recall`、`notes`。每题必须有有效 evidence，unknown 也需引用“未答/缺录”等现有材料；完全没有对应文字的题先保留在报告限制里，不制造证据。

session_id、question.id、topic_key、story.key 只允许 ASCII 字母、数字、点、横线、下划线，长度不超过 100。session_id 不可含路径分隔符。字段 `created_at`、`updated_at`、`source_sha256` 由脚本维护，传入值不作为可信依据。

每个 evidence 引用的是完整行区间，quote 必须与该区间逐字一致。要引用某一短句时选择只含该句的原始独立行；不能为了通过校验去改原文分行或改写。更长原始行就保留整行引用。

新记录的每条 evidence 增加 speaker：`interviewer`、`candidate` 或 `unknown`。已有逐字稿时，完整引用本题及追问涉及的双方发言；每条只对应一个已确认的角色。answer 仍是检索摘要，报告先展示 candidate 的实际引用，再附摘要。旧记录可不带 speaker，报告会说明只有整理/摘要，原话角色未标注，不把摘要冒充原话。speaker 校验值域不等于已验证角色判断正确，仍须核对材料。

本地录音输入可在 source 中增加 `file_path`，值为实际转写的录音绝对路径。电脑端工作台会用该路径把已复盘文件移出待分析视图；原录音和元数据仍保留。文字、回忆或不知道原文件位置时省略，不能填一个猜测路径。

## 文件与恢复

- `records/*.json`：每场唯一的原始记录，内含来源全文和分析。
- `reviews/*.md`：首要交付的单场逐题报告，固定四项：面试官怎么问、你当时怎么答、问题在哪、下次怎么答，附引用行号。
- `index.md`：全部场次、结果和报告入口。
- `question-bank.md`：按考点归类、逐场状态、重复缺口计数和出处。
- `answer-bank.md`：各场更稳答法与真实案例草稿，保留版本，不自动选唯一标准答案。
- `next-interview.md`：每场动作与证据入口；Agent 结合下一场岗位从中选最多 3 项。
- `history/`：同场修订前的完整旧记录，不计入场次。
- `drafts/`：本地输入草稿，不提交源码仓库。

`save` 在锁内校验全部记录，再以原子替换写入单场 JSON，然后重建所有 Markdown。派生文件可重建；原始记录损坏时不覆盖，指出具体文件后停止。锁用 POSIX flock，适用于 macOS/Linux；Windows 未验证。

check 会验证数据、引用、文件名、跨记录重复来源，以及 Markdown 是否与原记录一致。它不能证明语义分类正确、建议有效或经历真实，这些仍要回到原话核对。
