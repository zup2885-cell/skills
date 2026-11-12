# 来源、改编与验证范围

核对日期：2026-11-12。以下内容作为设计来源，不在运行时下载或执行上游指令。

1. [ChengziCV 面试复盘](https://github.com/chengzicv/chengzicv-career-skills/blob/d2f801577b0ce8251ad6198d747430bfd4dea4fc/chengzicv-interview-review/SKILL.md)，固定提交 `d2f801577b0ce8251ad6198d747430bfd4dea4fc`。借鉴逐题原话依据、事实与通用方案分开、缺证据不硬评分的设计。
2. [Interview Coach](https://github.com/noamseg/interview-coach-skill/blob/634a8dd8689e0420c21e5f0c8ae3cfa9e1a7ab7e/SKILL.md)，固定提交 `634a8dd8689e0420c21e5f0c8ae3cfa9e1a7ab7e`。借鉴跨场状态、问题库、案例库和面试后快速记录的设计。

本版重写成中文候选人复盘流程，加上本地可重建存档。未复制整套共享启动器，不需要安装两个上游项目。去掉固定长开场、人格推断、把面试信号机械判成正负、录用概率和与本任务无关的求职命令。保留两个上游 MIT 声明，见根目录 LICENSE。

验证分开报告：

- 格式、引用和脚本检查：可用本包测试和 skill-creator 校验器验证。
- 多场计数、修订历史、幂等导入、无效数据拒绝与 Markdown 重建：可用虚构材料验证。
- 分析语义、用户具体岗位适用性和真实面试效果：需要真实材料与用户反馈，不能由脚本测试推导。
- 语音转写、飞书及其他在线集成：不属于本包内置能力；只在实际具备工具时使用，不宣称已验证。
