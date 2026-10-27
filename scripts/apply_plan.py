#!/usr/bin/env python3
"""按家人确认过的改动计划（plan.json）修改手机，逐项核对，并生成恢复脚本。

用法：
  apply_plan.py plan.json --dry-run                 # 只列出将要做的事，不连手机也能看
  apply_plan.py plan.json -s <序列号> -o <工作目录>  # 执行；需要先运行 snapshot.sh

输出（工作目录下）：changes.log（逐项结果）、restore.sh（一键恢复）、manual.md（需要在手机上手动操作的项）。
受保护的核心组件（电话、短信、设置、桌面等）一律拒绝删除和限制。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

# 永不删除、永不限制（任何品牌）。按包名关键词匹配，宁可多拦。
PROTECTED = [
    r"\.dialer\b", r"\.contacts\b", r"\.mms\b", r"messaging", r"\.settings\b", r"systemui",
    r"launcher", r"inputmethod", r"\.ime\b", r"\.camera\b", r"gallery", r"clock", r"deskclock",
    r"filemanager", r"documentsui", r"packageinstaller", r"permissioncontroller", r"\.phone\b",
    r"telephony", r"telecom", r"\bsos\b", r"emergency", r"findphone", r"findmydevice",
    r"com\.google\.android\.gms", r"com\.google\.android\.gsf", r"\.secure\b", r"safecenter",
    r"securitycenter", r"systemmanager", r"providers\.", r"^android$", r"\.shell$",
]


def protected(pkg: str) -> bool:
    return any(re.search(p, pkg, re.I) for p in PROTECTED)


class Phone:
    def __init__(self, serial: str):
        self.serial = serial

    def sh(self, *args: str) -> str:
        r = subprocess.run(["adb", "-s", self.serial, "shell", *args], capture_output=True, text=True, stdin=subprocess.DEVNULL)
        return (r.stdout + r.stderr).strip()

    def adb(self, *args: str) -> str:
        r = subprocess.run(["adb", "-s", self.serial, *args], capture_output=True, text=True, stdin=subprocess.DEVNULL)
        return (r.stdout + r.stderr).strip()

    def installed(self, pkg: str) -> bool:
        return f"package:{pkg}" in self.sh("pm", "list", "packages", "--user", "0", pkg).split()

    def enabled(self, pkg: str) -> bool:
        return f"package:{pkg}" in self.sh("pm", "list", "packages", "-e", pkg).split()


def load_snapshot(work: Path) -> dict:
    snap = work / "snapshot"
    if not snap.exists():
        sys.exit("没有找到快照，请先运行 snapshot.sh。")
    settings = {}
    for line in (snap / "settings.txt").read_text(encoding="utf-8").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            settings[k] = v.strip()
    lines = lambda f: {l.strip() for l in (snap / f).read_text(encoding="utf-8").splitlines() if l.strip()}  # noqa: E731
    return {"settings": settings, "install_allow": lines("appops-install-allow.txt"), "overlay_allow": lines("appops-overlay-allow.txt")}


def plan_items(plan: dict):
    for kind in ("uninstall_user_apps", "uninstall_system_apps", "restrict_apps", "revoke_install", "revoke_overlay"):
        for it in plan.get(kind, []):
            yield kind, it


def dry_run(plan: dict) -> None:
    titles = {
        "uninstall_user_apps": "卸载第三方 App（只能从应用商店重装）",
        "uninstall_system_apps": "卸载系统自带应用（可恢复）",
        "restrict_apps": "删不掉的应用：关通知、禁后台",
        "revoke_install": "收回“安装其他应用”权限",
        "revoke_overlay": "收回悬浮窗（弹窗）权限",
    }
    for kind, title in titles.items():
        items = plan.get(kind, [])
        if items:
            print(f"\n## {title}（{len(items)} 项）")
            for it in items:
                mark = "  ← 受保护，执行时会拒绝" if protected(it["package"]) else ""
                print(f"- {it.get('label') or it['package']}（{it['package']}）{('：' + it['reason']) if it.get('reason') else ''}{mark}")
    st = plan.get("settings", {})
    if st:
        print("\n## 设置")
        for k, v in st.items():
            print(f"- {k} → {v}")
    if plan.get("manual"):
        print("\n## 需要在手机上手动操作")
        for m in plan["manual"]:
            print(f"- {m}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("-s", "--serial")
    ap.add_argument("-o", "--out")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    if a.dry_run:
        dry_run(plan)
        return
    if not (a.serial and a.out):
        sys.exit("执行时需要 -s <序列号> 和 -o <工作目录>。")

    work = Path(a.out)
    snap = load_snapshot(work)
    ph = Phone(a.serial)
    log, restore, reinstall = [], [], []

    def record(item: str, action: str, result: str, ok: bool):
        log.append(f"{dt.datetime.now():%F %T}\t{'成功' if ok else '失败'}\t{item}\t{action}\t{result}")
        print(f"{'✓' if ok else '✗'} {item}：{action} → {result}")

    for kind, it in plan_items(plan):
        pkg, label = it["package"], it.get("label") or it["package"]
        if protected(pkg):
            record(label, kind, "受保护的核心组件，已拒绝", False)
            continue
        if kind == "uninstall_user_apps":
            res = ph.adb("uninstall", pkg)
            ok = not ph.installed(pkg)
            record(label, "卸载第三方 App", res, ok)
            if ok:
                reinstall.append(label)
        elif kind == "uninstall_system_apps":
            res = ph.sh("pm", "uninstall", "-k", "--user", "0", pkg)
            ok = not ph.installed(pkg)
            if ok:
                record(label, "只对当前用户卸载", res, True)
                restore.append(f"adb -s \"$S\" shell cmd package install-existing {pkg}  # {label}")
                continue
            res2 = ph.sh("pm", "disable-user", "--user", "0", pkg)
            ok2 = not ph.enabled(pkg)
            record(label, "卸载失败，改为停用", f"{res} / {res2}", ok2)
            if ok2:
                restore.append(f"adb -s \"$S\" shell pm enable {pkg}  # {label}")
            else:
                record(label, "卸载和停用都被拒", "建议加入 restrict_apps，收进文件夹", False)
        elif kind == "restrict_apps":
            for op in ("POST_NOTIFICATION", "RUN_IN_BACKGROUND", "RUN_ANY_IN_BACKGROUND"):
                ph.sh("cmd", "appops", "set", pkg, op, "ignore")
                restore.append(f"adb -s \"$S\" shell cmd appops set {pkg} {op} default  # {label}")
            got = ph.sh("cmd", "appops", "get", pkg, "POST_NOTIFICATION")
            record(label, "关通知、禁后台（appops）", got.splitlines()[0] if got else "", "ignore" in got)
        elif kind in ("revoke_install", "revoke_overlay"):
            op = "REQUEST_INSTALL_PACKAGES" if kind == "revoke_install" else "SYSTEM_ALERT_WINDOW"
            was = "allow" if pkg in (snap["install_allow"] if kind == "revoke_install" else snap["overlay_allow"]) else "default"
            ph.sh("cmd", "appops", "set", pkg, op, "deny")
            got = ph.sh("cmd", "appops", "get", pkg, op)
            record(label, f"收回 {op}", got.splitlines()[0] if got else "", "deny" in got)
            restore.append(f"adb -s \"$S\" shell cmd appops set {pkg} {op} {was}  # {label}")

    st, old = plan.get("settings", {}), snap["settings"]
    if "font_scale" in st:
        ph.sh("settings", "put", "system", "font_scale", str(st["font_scale"]))
        got = ph.sh("settings", "get", "system", "font_scale")
        record("字号", f"font_scale {old.get('font_scale')} → {st['font_scale']}", got, got.startswith(str(st["font_scale"])))
        restore.append(f"adb -s \"$S\" shell settings put system font_scale {old.get('font_scale') or 1.0}")
    if "density" in st:
        size = ph.sh("wm", "size").splitlines()[-1].split()[-1]
        width = min(int(x) for x in size.split("x"))
        sw = width / int(st["density"]) * 160
        if sw < 320:
            record("显示大小", f"density {st['density']}", f"最小宽度 {sw:.0f}dp < 320dp，已拒绝", False)
        else:
            ph.sh("wm", "density", str(st["density"]))
            got = ph.sh("wm", "density")
            record("显示大小", f"density → {st['density']}（最小宽度 {sw:.0f}dp）", got.replace("\n", " "), str(st["density"]) in got)
            o = old.get("density_override")
            restore.append(f"adb -s \"$S\" shell wm density {o}" if o else "adb -s \"$S\" shell wm density reset")
    if "animation_scale" in st:
        for k in ("window_animation_scale", "transition_animation_scale", "animator_duration_scale"):
            ph.sh("settings", "put", "global", k, str(st["animation_scale"]))
            restore.append(f"adb -s \"$S\" shell settings put global {k} {old.get(k) if old.get(k) not in (None, 'null') else 1.0}")
        got = ph.sh("settings", "get", "global", "window_animation_scale")
        record("动画", f"→ {st['animation_scale']}", got, got.startswith(str(st["animation_scale"])))

    work.mkdir(parents=True, exist_ok=True)
    (work / "changes.log").open("a", encoding="utf-8").write("\n".join(log) + "\n")
    rs = ["#!/usr/bin/env bash", "# 一键恢复：把手机还原到执行计划之前的状态。用法：./restore.sh <序列号>",
          "set -u", "S=${1:?请传入手机序列号（adb devices 可查）}", ""] + list(reversed(restore))
    if reinstall:
        rs += ["", "# 以下第三方 App 已彻底卸载，脚本无法恢复，需要时请从应用商店重新下载："] + [f"#   {x}" for x in reinstall]
    (work / "restore.sh").write_text("\n".join(rs) + "\n", encoding="utf-8")
    (work / "restore.sh").chmod(0o755)
    if plan.get("manual"):
        (work / "manual.md").write_text("# 需要在手机上手动操作\n\n" + "\n".join(f"- [ ] {m}" for m in plan["manual"]) + "\n", encoding="utf-8")
    fails = sum(1 for l in log if "\t失败\t" in l)
    print(f"\n完成：{len(log)} 项，失败 {fails} 项。记录 {work/'changes.log'}，恢复脚本 {work/'restore.sh'}")


if __name__ == "__main__":
    main()
