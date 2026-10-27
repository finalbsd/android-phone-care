# vivo（OriginOS Ocean，Android 11，Y55s 实测）

> 实测日期：2026-10-26。

## 打开 USB 调试
- 设置 → 系统管理 → 关于手机 → 版本信息 → 连点“软件版本号”7 次 → 开发者选项 → USB 调试。
- 可能要求登录 vivo 账号或插着 SIM 卡。

## 删不掉的自带应用
- `pm uninstall -k --user 0` 报 `DELETE_FAILED_USER_RESTRICTED`，`pm disable-user` 报 `no root permission`，重启后仍然一样：
  vivo 健康（com.vivo.health）、音乐（com.android.bbkmusic）、浏览器（com.vivo.browser）、i主题（com.bbk.theme）、游戏中心（com.vivo.game）、Jovi（com.vivo.agent）、钱包（com.vivo.wallet）、邮件（com.vivo.email）、云服务（com.bbk.cloud）、游戏魔盒（com.vivo.gamecube）、锁屏杂志（com.vivo.magazine）。
- 部分预装应用（如支付宝、高德地图、秒玩小游戏）第一次卸载报 `DELETE_FAILED_INTERNAL_ERROR`，重启手机后再执行同一条命令成功。
- 个别包 `pm uninstall --user 0` 报 Success 后又出现在列表里，再执行一次后才消失。

## 广告和推荐的开关位置
- 负一屏：`settings get system hiboard_enabled`（1 开，0 关）。
- 锁屏杂志（com.vivo.magazine）会接管桌面壁纸：`settings get system desktop_wallpaper_res` 显示 `com.vivo.magazine`。换本地壁纸后变为 `com.vivo.gallery`。
- 系统广告：设置 → 安全 → 更多安全设置 → 广告与隐私。
- 后台弹窗管控：设置 → 安全 → 后台弹窗管控。
- 应用商店 → 我的 → 设置：“允许应用自动打开”“免下载安装”（实测缓存占 2GB 以上）。应用商店默认打开“应用更新”页，更新列表下面夹着推荐应用的“安装”按钮。

## 安装验证
- 设置 → 安全 → 更多安全设置 → 应用安装 → 应用安全验证。只管 vivo 应用商店以外的来源。没设锁屏密码时，验证方式要选“账号密码验证”。

## 通知设置页
- 在系统界面里（`com.android.systemui/.../NotificationSettingsActivity`），不在设置应用里。必须用 `am start -f 0x10008000 ...` 打开，否则一直停在上一个应用的页面。
- “允许通知”开关在页面右上方，点完按返回。
- “系统更新”“vivo 分享”的通知开关点不动。

## 字号
- 设置里滑块上限对应 `font_scale` 1.25；最后一档“超大字体”另存在 `font_scale_big`，只对电话、联系人、短信、便签生效。
- 在设置里点一下滑块，adb 设置的更大值会被改回 1.25。
- 1080 宽屏幕，`wm density 540` 时最小宽度 320dp，排版正常。

## 定时开关机、紧急呼叫、查找手机
- 定时开关机：设置 → 快捷与辅助 → 定时任务 → 定时开关机。
- 紧急呼叫、查找：设置 → 安全。添加紧急联系人后会弹“发送短信征求对方同意”，由家人决定。

## 其他坑
- 改字号后，后台的银行 App 可能被拉起并检测到 USB 调试，弹“支付风险”。
- 屏幕 30 秒自动锁屏，体检截图期间可临时 `settings put global stay_on_while_plugged_in 7`，结束改回原值。
