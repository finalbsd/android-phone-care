#!/usr/bin/env bash
# 只读体检：把手机的系统信息、内存、存储、应用、权限、通知、显示设置导出到 <工作目录>/raw/
# 用法：checkup.sh -s <序列号> -o <工作目录>
set -euo pipefail
serial=""; out=""
while getopts "s:o:" opt; do case $opt in s) serial=$OPTARG;; o) out=$OPTARG;; *) exit 2;; esac; done
[ -n "$serial" ] && [ -n "$out" ] || { echo "用法：checkup.sh -s <序列号> -o <工作目录>" >&2; exit 2; }
a() { adb -s "$serial" shell "$@" </dev/null; }
raw="$out/raw"; mkdir -p "$raw"
{
  echo "model=$(a getprop ro.product.model | tr -d '\r')"
  echo "brand=$(a getprop ro.product.brand | tr -d '\r')"
  echo "android=$(a getprop ro.build.version.release | tr -d '\r')"
  echo "sdk=$(a getprop ro.build.version.sdk | tr -d '\r')"
  echo "uptime=$(a uptime | tr -d '\r')"
  echo "font_scale=$(a settings get system font_scale | tr -d '\r')"
  echo "density=$(a wm density | tr -d '\r' | tail -1)"
  echo "size=$(a wm size | tr -d '\r' | tail -1)"
  for k in window_animation_scale transition_animation_scale animator_duration_scale stay_on_while_plugged_in; do
    echo "$k=$(a settings get global $k | tr -d '\r')"; done
} > "$raw/device.txt"
a cat /proc/meminfo > "$raw/meminfo.txt"
a df -h /data > "$raw/df.txt"
a dumpsys meminfo > "$raw/dumpsys-meminfo.txt"
a pm list packages -3 -i > "$raw/packages-third.txt"
a pm list packages -s > "$raw/packages-system.txt"
a pm list packages -d > "$raw/packages-disabled.txt" || true
a dumpsys usagestats > "$raw/usagestats.txt"
a cmd appops query-op REQUEST_INSTALL_PACKAGES allow > "$raw/appops-install.txt" || true
a cmd appops query-op SYSTEM_ALERT_WINDOW allow > "$raw/appops-overlay.txt" || true
a dumpsys notification > "$raw/notification.txt"
a cmd package query-receivers --brief -a android.intent.action.BOOT_COMPLETED > "$raw/boot-receivers.txt" 2>/dev/null || true
a cmd package query-activities --brief -a android.intent.action.MAIN -c android.intent.category.LAUNCHER > "$raw/launcher-activities.txt" || true
a dumpsys package > "$raw/dumpsys-package.txt"
echo "体检原始数据已保存到 $raw"
