---
name: douyin-creator-scraping
description: 从本人已登录的抖音创作者中心导出作品指标，保存本地历史快照并检查数据新鲜度。适用于作品数据采集和复盘准备。
---

# 抖音作品数据采集

先读 `/Users/m3air/GitHub/skills/tzfilm-douyin-tool/references/local-workflow.md` 第 1 阶段；需要排错时再读同项目 `references/original-creator-SKILL.md`。

使用独立 Python 运行 `tzfilm-douyin-tool/local-runtime/douyin_hourly.py`。数据库在 `/Users/m3air/Library/Application Support/TzFilmDouyin/douyin_stats.db`，日志在其 `logs/` 中。

核对账号、Excel 内容、库中最新采集时间、作品数量和指标单位。原脚本部分错误路径返回 0，必须检查实际文件和新快照；登录过期时由用户重新登录。

操作会激活 Chrome，应先说明。不要按上游经验文档修改全局下载目录、自动建周期任务或发送 Telegram。上游对 macOS 权限的描述仅是排错线索，不是通用保证。
