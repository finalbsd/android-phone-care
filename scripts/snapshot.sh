#!/usr/bin/env bash
# 改动前存快照：应用列表、相关设置、安装权限和悬浮窗权限、通知状态，供 apply_plan.py 生成恢复脚本。
# 用法：snapshot.sh -s <序列号> -o <工作目录>
set -euo pipefail
serial=""; out=""
while getopts "s:o:" opt; do case $opt in s) serial=$OPTARG;; o) out=$OPTARG;; *) exit 2;; esac; done
[ -n "$serial" ] && [ -n "$out" ] || { echo "用法：snapshot.sh -s <序列号> -o <工作目录>" >&2; exit 2; }
a() { adb -s "$serial" shell "$@" </dev/null; }
snap="$out/snapshot"
if [ -e "$snap" ]; then
  echo "快照已存在：$snap。为了保证能恢复到最初状态，不覆盖旧快照。确实要重拍，请换一个工作目录。" >&2; exit 1
fi
mkdir -p "$snap"
{
  echo "font_scale=$(a settings get system font_scale | tr -d '\r')"
  echo "density_override=$(a wm density | tr -d '\r' | sed -n 's/Override density: //p')"
  for k in window_animation_scale transition_animation_scale animator_duration_scale stay_on_while_plugged_in; do
    echo "$k=$(a settings get global $k | tr -d '\r')"; done
} > "$snap/settings.txt"
a pm list packages > "$snap/packages-enabled-or-installed.txt"
a pm list packages -u > "$snap/packages-all-users.txt"
a pm list packages -d > "$snap/packages-disabled.txt" || true
a cmd appops query-op REQUEST_INSTALL_PACKAGES allow > "$snap/appops-install-allow.txt" || true
a cmd appops query-op SYSTEM_ALERT_WINDOW allow > "$snap/appops-overlay-allow.txt" || true
# 只保留每个应用的通知开关（AppSettings 行），不导出通知标题和正文
a dumpsys notification | grep -E "^ *AppSettings: " > "$snap/notification.txt" || true
date '+%F %T' > "$snap/taken-at.txt"
echo "快照已保存到 $snap"
