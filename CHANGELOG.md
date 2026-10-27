# 更新记录

## 0.1.0（2026-10-27）

- 首个版本：SKILL.md（11 步流程、10 条硬规则）、AGENTS.md、vendors（vivo、华为、模板）、scripts（checkup.sh 只读体检、analyze.py 体检报告和回访对比、app_labels.py 读应用名、snapshot.sh 快照、apply_plan.py 按计划执行并生成恢复脚本）、templates（改动计划示例、给老人的大字说明）、README、MIT 许可。
- 为什么：把 2026-10-26 给一台 vivo Y55s 和一台华为 Mate 20 RS 做清理的过程固定成可复用的流程，供 Claude Code、Codex、WorkBuddy 等智能体使用。
- 已验证：脚本语法检查；apply_plan.py 的 --dry-run 和保护名单；analyze.py 用 vivo 那次的真实体检数据（部分字段）跑通；“申请的敏感权限”解析用样例文本测试。
- 未验证：没有连接手机实测 checkup.sh、snapshot.sh、app_labels.py、apply_plan.py 的执行和 restore.sh 的恢复；其他品牌完全未测。
- 升级动作：无（首个版本）。发布到 GitHub：finalbsd/android-phone-care。
