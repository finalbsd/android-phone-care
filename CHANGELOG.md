# 更新记录

## 0.1.1（2026-10-27）

- 隐私：体检和快照读取通知时只保留每个应用的开关状态（AppSettings 行），不再导出通知标题和正文；README 和 SKILL.md 写明智能体读到的信息会发给它所用的模型服务商，并要求机主知情同意。
- 安全：apply_plan.py 执行必须加 --confirmed（家人看过预览并同意后）；系统应用只允许卸载桌面上有图标的，后台组件默认拒绝；保护名单补充 WebView、蓝牙、NFC、Wi-Fi、紧急广播、IMS、证书、系统更新等；包名做格式校验，防止计划文件里混入命令。
- 可恢复：snapshot.sh 不覆盖已有快照；每次执行单独生成 restore-<时间>.sh，不再覆盖。
- 文档：字号建议从 1.3 试起；模拟点击前先截图确认页面；不要限制需要收消息的应用；紧急呼叫误拨提醒。
- 为什么：公开分享前重新审查，发现会导出聊天通知内容、重复执行会丢失恢复点、可能误删无图标的系统组件等风险。
- 已验证：语法检查；--dry-run；未加 --confirmed 时拒绝执行；保护名单和包名校验用样例测试。
- 未验证：仍未连手机完整跑过一遍。
- 升级动作：已有工作目录的用户，下次清理请用新的工作目录；执行命令需要加 --confirmed。

## 0.1.0（2026-10-27）

- 首个版本：SKILL.md（11 步流程、10 条硬规则）、AGENTS.md、vendors（vivo、华为、模板）、scripts（checkup.sh 只读体检、analyze.py 体检报告和回访对比、app_labels.py 读应用名、snapshot.sh 快照、apply_plan.py 按计划执行并生成恢复脚本）、templates（改动计划示例、给老人的大字说明）、README、MIT 许可。
- 为什么：把 2026-10-26 给一台 vivo Y55s 和一台华为 Mate 20 RS 做清理的过程固定成可复用的流程，供 Claude Code、Codex、WorkBuddy 等智能体使用。
- 已验证：脚本语法检查；apply_plan.py 的 --dry-run 和保护名单；analyze.py 用 vivo 那次的真实体检数据（部分字段）跑通；“申请的敏感权限”解析用样例文本测试。
- 未验证：没有连接手机实测 checkup.sh、snapshot.sh、app_labels.py、apply_plan.py 的执行和 restore.sh 的恢复；其他品牌完全未测。
- 升级动作：无（首个版本）。发布到 GitHub：finalbsd/android-phone-care。
