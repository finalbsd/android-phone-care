# android-phone-care：用智能体帮爸妈清理安卓手机

把爸妈的安卓手机用数据线连上电脑，让智能体（Claude Code、Codex、WorkBuddy 等能运行命令行的智能体）按这个 Skill 帮你：

- 体检：手机为什么慢，哪些 App 从没打开过，哪些在后台偷偷运行、能偷偷装别的 App。
- 删掉老人用不上的 App（系统自带的用可恢复方式）。
- 关掉推送、广告、负一屏推荐、后台弹窗。
- 收回 App 乱装应用的权限。
- 把字号调到比系统设置能拉到的还大。
- 打开紧急呼叫、查找手机，设每晚自动重启。
- 生成一键恢复脚本，和一页给老人看的大字说明。

每一项改动都先出计划，你确认后才执行。

> **状态：早期版本（0.1.0）。** 清理流程来自 2026 年 10 月在一台 vivo Y55s 和一台华为 Mate 20 RS 上的手动实测；`scripts/` 里的脚本是按这两次经验整理的，还没有连手机完整跑过一遍。第一次使用请每一步都看清楚再确认，也欢迎提 issue 反馈。

## 先看：怎么恢复

- 每次执行完会在工作目录生成 `restore-<时间>.sh`，运行 `./restore-<时间>.sh <手机序列号>` 可以把系统应用、字号、显示大小、动画、权限恢复到改动前的状态。执行过多次的，按时间从新到旧依次运行。
- 第三方 App 是彻底卸载的，App 里的数据（登录状态、聊天记录等）会一起删掉，只能从应用商店重新下载，恢复脚本末尾列出了名单。删之前请确认重要数据已备份。
- 恢复出厂设置也会让所有系统应用回来（会清空手机数据，一般用不到）。

## 使用前请注意

- **请在机主知情同意下使用**，不要用在别人的手机上。
- **隐私**：智能体读取的应用列表、使用记录、截图，会作为对话内容发送给它所用的模型服务商。脚本不导出短信、通话记录、相册和通知正文。
- **紧急呼叫**：打开“连按电源键自动拨号”后可能误拨，请把家人号码排在 110 前面，并告诉老人误拨了怎么说。

## 风险说明

- 本 Skill 不 root、不解锁、不刷机，不删除系统分区里的文件，不碰电话、短信、设置、桌面、WebView、蓝牙、Wi-Fi、紧急广播等核心组件（脚本里有保护名单）；系统应用只允许卸载桌面上有图标的。
- 执行前必须先预览计划，家人确认后才加 `--confirmed` 执行。
- 不同品牌、不同系统版本差别很大。目前只在 vivo（OriginOS，Android 11）和华为（HarmonyOS 4）上手动实测过流程，其他品牌未测试，请先在不重要的手机上试，或者每一步都看清楚再确认。
- 开着 USB 调试时，部分银行 App 会提示“支付风险”。清理完请关闭开发者选项。
- 这是一个按“现状”提供的工具，使用造成的问题由使用者自行承担（见 LICENSE）。

## 需要准备

- 电脑上装好 adb（macOS：`brew install android-platform-tools`；Windows：下载 Android SDK Platform-Tools）。
- Python 3（脚本只用标准库）。
- 可选：scrcpy（把手机屏幕投到电脑上，用鼠标点手机）；aapt2 或 `pip install androguard`（读出 App 的中文名）。
- 手机上打开 USB 调试：设置 → 关于手机 → 连点版本号 7 次 → 开发者选项 → USB 调试。各品牌路径见 `vendors/`。

## 怎么用

把这个仓库放到你的智能体能读到的 Skill 目录（例如 Claude Code 的 `~/.claude/skills/android-phone-care`），或者在仓库目录里直接启动智能体（它会读 `AGENTS.md`）。然后连上手机，对它说：

> 这是我爸的手机，帮他清理一下：太卡、广告多、字太小。

它会按 `SKILL.md` 的流程，先体检、再出计划、你确认后执行。

也可以手动运行脚本：

```bash
scripts/checkup.sh -s <序列号> -o work/dad        # 只读体检
scripts/app_labels.py -s <序列号> -o work/dad/labels.json   # 可选：读 App 中文名
scripts/analyze.py work/dad --labels work/dad/labels.json   # 生成 report.md
# 按 templates/plan.example.json 写 plan.json
scripts/apply_plan.py plan.json --dry-run          # 先看计划
scripts/snapshot.sh -s <序列号> -o work/dad        # 存快照
scripts/apply_plan.py plan.json -s <序列号> -o work/dad --confirmed   # 家人确认后执行
# 一个月后回访
scripts/checkup.sh -s <序列号> -o work/dad-1m && scripts/analyze.py work/dad-1m --compare work/dad
```

## 已实测机型

| 品牌 | 机型 | 系统 | 日期 |
|---|---|---|---|
| vivo | Y55s | OriginOS Ocean（Android 11） | 2026-10 |
| 华为 | Mate 20 RS | HarmonyOS 4.0（底层 Android 10） | 2026-10 |

欢迎补充其他品牌：复制 `vendors/_template.md`，只写实测过的内容。

## iPhone 呢？

iPhone 没有类似 adb 的通道，电脑不能帮它卸载 App 或改系统设置。可以手动做这几件事：

- 设置 → 显示与亮度 → 文字大小；设置 → 辅助功能 → 显示与文字大小 → 更大字体。
- 设置 → 通知：逐个关掉不需要的 App。
- 设置 → 屏幕使用时间 → 内容和隐私访问限制 → iTunes 与 App Store 购买项目 → 安装 App：设为“不允许”，防止乱装。
- 设置 → 紧急联络：打开“按住并松开”或“按五次”，填好紧急联系人。

## 许可

MIT，见 LICENSE。
