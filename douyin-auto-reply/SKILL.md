---
name: douyin-auto-reply
description: 导出本人抖音作品的评论，去重分类并生成回复草稿；在用户明确授权发送后执行批量回复并核对结果。
---

# 抖音评论导出与回复

先读 `/Users/m3air/GitHub/skills/tzfilm-douyin-tool/references/local-workflow.md` 第 3 阶段；命令、JSON 格式和兼容问题参考同项目 `skills/douyin-auto-reply.md`。原作者专属会员群推广规则不适用于本用户。

进入 `/Users/m3air/GitHub/skills/tzfilm-douyin-tool/auto-reply` 再运行 npm。登录态和评论数据通过被 Git 忽略的软链接放在 `/Users/m3air/Library/Application Support/TzFilmDouyin`。

导出后去重、核对作品、分类评论，根据用户账号定位生成回复草稿。不虚构亲历、承诺或自行增加营销引导。

安装、登录、导出和生成草稿不代表允许发送。仅在用户明确授权发送该批回复后发送；同一批次已有清晰授权时不重复询问。dry-run 不发送，但仍可能打开浏览器。核对结果 JSON 和 SQLite，分别统计成功、跳过、未匹配、失败。
