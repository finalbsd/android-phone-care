#!/usr/bin/env python3
"""把 checkup.sh 导出的原始数据整理成 checkup.json 和一份大白话的 report.md。

用法：
  analyze.py <工作目录>                       # 读 <工作目录>/raw/，写 checkup.json 和 report.md
  analyze.py <工作目录> --compare <上次目录>   # 回访：和上次体检对比
  analyze.py <工作目录> --labels labels.json  # 可选：app_labels.py 生成的应用名

只用 Python 标准库。可疑 App 按行为特征标出，不使用任何名单。
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

EPOCH_PREFIX = "1970-01-01"


def read(raw: Path, name: str) -> str:
    p = raw / name
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


def kv_file(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def meminfo(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        m = re.match(r"(\w+):\s+(\d+) kB", line)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def df_used(text: str) -> str:
    lines = [l for l in text.splitlines() if l.strip() and not l.startswith("Filesystem")]
    if not lines:
        return ""
    parts = lines[-1].split()
    return " ".join(parts[1:5]) if len(parts) >= 5 else lines[-1]


def third_party(text: str) -> dict:
    apps = {}
    for line in text.splitlines():
        m = re.match(r"package:(\S+)(?:\s+installer=(\S+))?", line.strip())
        if m:
            apps[m.group(1)] = {"installer": m.group(2) or ""}
    return apps


def usage(text: str) -> dict:
    """取各统计周期里最近的 lastTimeUsed 和最大的 appLaunchCount。"""
    out: dict[str, dict] = {}
    for m in re.finditer(r'package=(\S+)[^\n]*?lastTimeUsed="([^"]*)"[^\n]*?appLaunchCount=(\d+)', text):
        pkg, last, count = m.group(1), m.group(2), int(m.group(3))
        rec = out.setdefault(pkg, {"last_used": "", "launches": 0})
        if not last.startswith(EPOCH_PREFIX) and last > rec["last_used"]:
            rec["last_used"] = last
        rec["launches"] = max(rec["launches"], count)
    return out


def package_lines(text: str) -> set:
    return {l.strip() for l in text.splitlines() if re.fullmatch(r"[\w.]+", l.strip())}


def boot_packages(text: str) -> set:
    return {m.group(1) for m in re.finditer(r"^\s*([\w.]+)/", text, re.M)}


def notifications(text: str) -> tuple[set, set]:
    on, off = set(), set()
    for m in re.finditer(r"AppSettings: (\S+) \((\d+)\)([^\n]*)", text):
        pkg, uid, rest = m.group(1), int(m.group(2)), m.group(3)
        if uid < 10000:
            continue
        (off if "importance=NONE" in rest else on).add(pkg)
    return on - off, off


WATCH = {
    "android.permission.REQUEST_INSTALL_PACKAGES": "申请安装其他应用",
    "android.permission.SYSTEM_ALERT_WINDOW": "申请在别的应用上方弹窗",
    "android.permission.RECEIVE_BOOT_COMPLETED": "申请开机自启",
}


def package_info(text: str) -> dict:
    """从 dumpsys package 里取每个包的安装时间和申请的敏感权限。"""
    out = {}
    for block in re.split(r"\n  Package \[", text)[1:]:
        pkg = block.split("]", 1)[0]
        m = re.search(r"firstInstallTime=([\d-]+ [\d:]+)", block)
        req = re.search(r"requested permissions:\n((?:\s{6,}\S.*\n?)*)", block)
        perms = set(re.findall(r"(android\.permission\.\w+)", req.group(1))) if req else set()
        out[pkg] = {"first_install": m.group(1) if m else "", "requested": sorted(p for p in perms if p in WATCH)}
    return out


def top_memory(text: str, n: int = 8) -> list:
    sec = text.split("Total PSS by process:", 1)
    if len(sec) < 2:
        return []
    rows = []
    for line in sec[1].splitlines()[1:]:
        m = re.match(r"\s*([\d,]+)K: (\S+)", line)
        if not m:
            break
        rows.append({"process": m.group(2), "mb": round(int(m.group(1).replace(",", "")) / 1024)})
    return rows[:n]


def build(work: Path, labels: dict) -> dict:
    raw = work / "raw"
    dev = kv_file(read(raw, "device.txt"))
    mem = meminfo(read(raw, "meminfo.txt"))
    apps = third_party(read(raw, "packages-third.txt"))
    use = usage(read(raw, "usagestats.txt"))
    can_install = package_lines(read(raw, "appops-install.txt"))
    overlay = package_lines(read(raw, "appops-overlay.txt"))
    boot = boot_packages(read(raw, "boot-receivers.txt"))
    notif_on, notif_off = notifications(read(raw, "notification.txt"))
    info = package_info(read(raw, "dumpsys-package.txt"))

    for pkg, rec in apps.items():
        u = use.get(pkg, {"last_used": "", "launches": 0})
        never = not u["last_used"] and u["launches"] == 0
        flags = []
        if never:
            flags.append("从没打开过")
        req = info.get(pkg, {}).get("requested", [])
        if pkg in can_install:
            flags.append("已获准安装其他应用")
        elif "android.permission.REQUEST_INSTALL_PACKAGES" in req:
            flags.append(WATCH["android.permission.REQUEST_INSTALL_PACKAGES"])
        if pkg in overlay:
            flags.append("已获准在别的应用上方弹窗")
        elif "android.permission.SYSTEM_ALERT_WINDOW" in req:
            flags.append(WATCH["android.permission.SYSTEM_ALERT_WINDOW"])
        if pkg in boot or "android.permission.RECEIVE_BOOT_COMPLETED" in req:
            flags.append("开机自启")
        rec.update(
            label=labels.get(pkg, ""),
            first_install=info.get(pkg, {}).get("first_install", ""),
            last_used=u["last_used"],
            launches=u["launches"],
            notifications_on=pkg in notif_on,
            flags=flags,
            suspicious=never and len(flags) >= 2,
        )
    return {
        "device": dev,
        "memory": {
            "total_gb": round(mem.get("MemTotal", 0) / 1024 / 1024, 1),
            "available_gb": round(mem.get("MemAvailable", 0) / 1024 / 1024, 1),
            "swap_used_gb": round((mem.get("SwapTotal", 0) - mem.get("SwapFree", 0)) / 1024 / 1024, 1),
            "swap_total_gb": round(mem.get("SwapTotal", 0) / 1024 / 1024, 1),
        },
        "storage": df_used(read(raw, "df.txt")),
        "top_memory": top_memory(read(raw, "dumpsys-meminfo.txt")),
        "third_party": apps,
        "can_install_others": sorted(can_install),
        "overlay": sorted(overlay),
        "notifications_on": sorted(notif_on),
    }


def name(pkg: str, rec: dict) -> str:
    return f"{rec['label']}（{pkg}）" if rec.get("label") else pkg


def report(data: dict, prev: dict | None) -> str:
    d, m, apps = data["device"], data["memory"], data["third_party"]
    L = ["# 手机体检报告", ""]
    L.append(f"- 机型：{d.get('brand','')} {d.get('model','')}，Android {d.get('android','')}")
    L.append(f"- 开机时长：{d.get('uptime','')}")
    L.append(f"- 内存：共 {m['total_gb']}GB，可用 {m['available_gb']}GB；虚拟内存已用 {m['swap_used_gb']}/{m['swap_total_gb']}GB")
    L.append(f"- 存储（容量 已用 可用 占比）：{data['storage']}")
    L.append(f"- 字号 font_scale：{d.get('font_scale','')}；显示 {d.get('size','')}，{d.get('density','')}")
    L.append(f"- 第三方 App：{len(apps)} 个；开着通知的应用：{len(data['notifications_on'])} 个")
    L += ["", "## 后台占内存最多的进程", ""]
    L += [f"- {r['process']}：约 {r['mb']}MB" for r in data["top_memory"]]

    sus = {p: r for p, r in apps.items() if r["suspicious"]}
    L += ["", f"## 可疑的 App（{len(sus)} 个）", "", "从没打开过，又申请或拿到了至少一项：安装其他应用、在别的应用上方弹窗、开机自启。", ""]
    for p, r in sorted(sus.items(), key=lambda x: x[1]["first_install"]):
        L.append(f"- {name(p, r)}：{'、'.join(r['flags'])}；安装于 {r['first_install'] or '未知'}；来源 {r['installer'] or '未知'}")
    never = {p: r for p, r in apps.items() if "从没打开过" in r["flags"] and not r["suspicious"]}
    L += ["", f"## 其他从没打开过的 App（{len(never)} 个）", ""]
    L += [f"- {name(p, r)}" for p, r in sorted(never.items())]
    L += ["", "## 能安装其他应用的 App", ""]
    L += [f"- {name(p, apps.get(p, {'label': ''}))}" for p in data["can_install_others"]] or ["- 没有"]

    if prev:
        L += ["", "## 和上次体检相比", ""]
        new = sorted(set(apps) - set(prev["third_party"]))
        gone = sorted(set(prev["third_party"]) - set(apps))
        L.append(f"- 新装的 App：{len(new)} 个" + ("：" + "、".join(name(p, apps[p]) for p in new) if new else ""))
        L.append(f"- 不见了的 App：{len(gone)} 个")
        renot = sorted(set(data["notifications_on"]) - set(prev["notifications_on"]))
        L.append(f"- 重新开了通知的应用：{len(renot)} 个" + ("：" + "、".join(renot) if renot else ""))
        for k in ("font_scale", "density"):
            if prev["device"].get(k) != d.get(k):
                L.append(f"- {k} 变了：{prev['device'].get(k)} → {d.get(k)}")
    L += ["", "> 这份报告只读取了手机信息，没有做任何改动。"]
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("work")
    ap.add_argument("--compare")
    ap.add_argument("--labels")
    a = ap.parse_args()
    work = Path(a.work)
    labels = json.loads(Path(a.labels).read_text(encoding="utf-8")) if a.labels else {}
    data = build(work, labels)
    (work / "checkup.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    prev = json.loads((Path(a.compare) / "checkup.json").read_text(encoding="utf-8")) if a.compare else None
    (work / "report.md").write_text(report(data, prev), encoding="utf-8")
    print(f"已生成 {work/'checkup.json'} 和 {work/'report.md'}")


if __name__ == "__main__":
    main()
