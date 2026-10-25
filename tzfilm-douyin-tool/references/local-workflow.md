# 本机完整工作流

## 路径

- 完整源码：`/Users/m3air/GitHub/skills/tzfilm-douyin-tool`
- Python：`/Users/m3air/Library/Application Support/TzFilmDouyin/venv/bin/python`
- 本机 Python 入口：源码目录的 `local-runtime/`；根目录 Python 保留上游原件。
- 评论模块：源码目录的 `auto-reply/`。
- 数据、日志和浏览器登录态：`/Users/m3air/Library/Application Support/TzFilmDouyin`。
- 上游来源、固定版本与完整性记录：`UPSTREAM.json`。
- 原根 SKILL 和忽略规则备份：`references/original-creator-SKILL.md`、`references/original.gitignore`。

本机适配修正了作者的 Hermes 路径、数据库位置不一致、默认追踪作者作品等问题，并为追踪器补上必填 `--title` 参数。原脚本会调用的飞书和 Telegram 发送默认关闭。

## 1. 登录与作品采集

需要 Chrome 已登录 `https://creator.douyin.com/creator-micro/data-center/content`，并允许 Apple 事件中的 JavaScript；首次运行可能要求 macOS 允许控制 Chrome。登录和授权由本人完成，不修改全局 Chrome 下载目录，不复制其他应用凭据。

```bash
"/Users/m3air/Library/Application Support/TzFilmDouyin/venv/bin/python" "/Users/m3air/GitHub/skills/tzfilm-douyin-tool/local-runtime/douyin_hourly.py"
```

此步会激活 Chrome，导出登录账号自己的作品数据，不是任意博主全站抓取。不要仅凭退出码判定成功：原版部分失败路径返回 0。检查日志、真实 Excel、库中最新时间和新增数量，确认本次采集新鲜且属于正确账号。

如果 Chrome 的 Apple 事件 JavaScript 未启用，可改用已连接的浏览器/电脑操作工具，在当前登录页面的“内容管理 → 导出数据”下载 Excel，再调用本机 `parse_xlsx()` 与 `save_to_db()`。2026-10-25 实测入口为 `/creator-micro/content/manage`，导出文件为 `作品列表导出.xlsx`。不必为单次导出扩大浏览器脚本权限；界面操作必须根据最新可见状态执行，用户切换标签页时先重新确认状态。

原始 Excel 复制到本机数据目录 `exports/` 后再解析，保留完整字段和原始精度。`-` 表示缺失，不代表零；本机适配已修正封面点击率缺失值误变成 0% 的情况。首次快照不能推出历史增长趋势。

## 2. 历史分析与新视频追踪

```bash
"/Users/m3air/Library/Application Support/TzFilmDouyin/venv/bin/python" "/Users/m3air/GitHub/skills/tzfilm-douyin-tool/local-runtime/douyin_new_video_tracker.py" --title "核实过的作品完整标题" --init --no-scrape
"/Users/m3air/Library/Application Support/TzFilmDouyin/venv/bin/python" "/Users/m3air/GitHub/skills/tzfilm-douyin-tool/local-runtime/prediction_query.py" latest
```

有新快照时再次运行追踪器，去掉 `--init`。已有新鲜采集时保留 `--no-scrape`。标题不可留空；上游按前 12 字模糊匹配，必须核对命中的完整标题。

连续指标完全相同要先排查采集失败和登录过期。预测需要说明历史样本数量；样本不足时只能粗略估算。作者设定的置信度不是已验证的统计概率，不可补造时序数据。

## 3. 评论导出与回复草稿

评论模块使用独立 Playwright 浏览器登录态，与第一步 Chrome 不共用，需要单独扫码一次。

```bash
cd /Users/m3air/GitHub/skills/tzfilm-douyin-tool/auto-reply
npm run auth
npm run comments:export -- "作品标题关键词" --limit 300 --timeout 120000
```

按数据库已回复记录和旧计划去重、分类评论，生成符合本用户账号定位的回复。原作者的会员群推广规则不适用。草稿保存在 `comments-output/auto-reply-plan.json`，字段见上游 `skills/douyin-auto-reply.md`。

用户明确授权发送这批草稿后，才执行：

```bash
cd /Users/m3air/GitHub/skills/tzfilm-douyin-tool/auto-reply
npm run comments:reply -- --limit 30 --timeout 600000 comments-output/auto-reply-plan.json
```

预览可加 `--dry-run`，仍可能打开浏览器。执行后核对结果 JSON 和数据库，区分成功、跳过、未匹配、失败，避免重复发送。

## 4. 飞书同步（可选）

上游同步脚本会删除过期行、空行及旧的追踪/账号记录。先确认目标表、字段和清理范围，优先使用专用表；写入及清理须有用户授权。源文档和代码可能不一致，以实际代码为准。

应用凭据在本机私有文件 `/Users/m3air/Library/Application Support/TzFilmDouyin/.env` 配置，变量见根 `.env.example`。未配置时如实标为未连接，不要求在聊天中粘贴秘密。

```bash
DOUYIN_ENABLE_FEISHU_SYNC=1 "/Users/m3air/Library/Application Support/TzFilmDouyin/venv/bin/python" "/Users/m3air/GitHub/skills/tzfilm-douyin-tool/local-runtime/feishu_sync.py"
```

安装整套工作流不等于允许发送评论、同步飞书或建立定时任务。用户提出持续运行时再使用当前环境的自动化能力，不照搬 Hermes cron。Telegram 仅在用户要求且完成配置后启用。

## 验收边界

安装验收：五个技能入口、原始文件哈希、Python/Node 依赖、数据库、语法和浏览器离线启动。
业务验收：本人登录后逐阶段验证。安装成功不等于采集成功、预测准确、回复已发送或飞书已同步。
