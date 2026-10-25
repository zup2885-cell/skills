---
name: feishu-douyin-sync
description: 将本人抖音作品快照、新作品追踪和账号指标同步到已授权飞书多维表，检查字段映射及原脚本的记录清理范围。
---

# 抖音数据同步飞书

先读 `/Users/m3air/GitHub/skills/tzfilm-douyin-tool/references/local-workflow.md` 第 4 阶段；字段参考同项目 `skills/feishu-douyin-sync.md`，实际清理行为以根目录 `feishu_sync.py` 为准，原文与代码可能不一致。

本机使用 `local-runtime/feishu_sync.py`；凭据文件为 `/Users/m3air/Library/Application Support/TzFilmDouyin/.env`。未配置就停止并说明，不借用其他工具凭据，不要求在聊天中粘贴秘密。

核对数据库新鲜度、目标 Base/表 ID、字段和数量。上游会删除过期、空白及旧追踪/账号记录；先明确影响，优先用专用目标表。有该写入及清理范围的用户授权后，用 `DOUYIN_ENABLE_FEISHU_SYNC=1` 显式启用。

执行后在目标表验证新增、更新、删除数量；失败不影响本地保存。不把 API 接收请求等同于全量成功，不未经请求建周期同步。
