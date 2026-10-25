---
name: douyin-video-prediction
description: 基于本人抖音作品历史快照追踪指定新视频的增长，估算播放层级并解释样本不足与采集异常。适用于新作品追踪和历史表现复盘。
---

# 抖音新视频追踪与预测

先读 `/Users/m3air/GitHub/skills/tzfilm-douyin-tool/references/local-workflow.md` 第 2 阶段；模型细节参考同项目 `skills/douyin-video-prediction.md`。

用独立 Python 运行 `local-runtime/douyin_new_video_tracker.py --title "已核实标题"`，首次加 `--init`，已有新鲜快照时加 `--no-scrape`。本机入口已加入必填标题参数，不修改上游硬编码标题。

核对实际命中的完整标题和最新时间；前 12 字相同可能匹配错误。连续零增长先查采集失败，不能补造检查点。

区分实测指标和模型估算，报告历史样本数、采集时间和限制。作者的置信度不是已验证统计概率。对比时考虑时长、发布时间、单位和曝光基数。

仅在用户要求时设置持续追踪；上游 Hermes cron 和 Telegram 不是本机自动授权的步骤。飞书同步可选且默认关闭。
