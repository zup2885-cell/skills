---
name: tzfilm-douyin-tool
description: TzFilm 抖音运营工作流总入口，串联作品数据采集、历史分析、新视频追踪预测、评论草稿和飞书同步。用户要使用整套抖音运营流程时使用。
---

# TzFilm 抖音运营工作流

完整源码：`/Users/m3air/GitHub/skills/tzfilm-douyin-tool`。
先读 [本机完整流程](references/local-workflow.md)，再按当前阶段读取相应技能。

| 阶段 | 技能 | 交付 |
|---|---|---|
| 采集 | `douyin-creator-scraping` | 本人作品指标及历史快照 |
| 追踪分析 | `douyin-video-prediction` | 增长对比、样本数量和预测边界 |
| 评论 | `douyin-auto-reply` | 评论导出、分类和回复草稿 |
| 飞书 | `feishu-douyin-sync` | 已授权目标表中的同步结果 |

完整顺序：检查环境及本人登录 → 采集作品数据 → 核对账号、时间和指标 → 历史分析 → 指定作品追踪 → 评论导出与草稿 → 在授权范围内发送或同步 → 汇报实际结果与未完成部分。

仅执行用户当前要求的阶段。安装不等于授权发送评论、写飞书或建定时任务。报告默认交付当前对话。需要定时执行时使用当前环境的自动化能力，不照搬上游 Hermes cron。

本机入口使用 `local-runtime/` 的适配脚本；根 Python 和 `skills/*.md` 保留上游原件。作者路径、会员群引导、收件人及清理规则不是用户配置。保留本人登录步骤，不改全局 Chrome 下载目录或绕过系统授权。首次采集会激活 Chrome，先说明。
