#!/usr/bin/env python3
"""读出 App 在手机上显示的名字（包名常是乱码）。

把 APK 拉到本机临时目录，只读取清单信息，不安装、不运行。
需要以下二者之一：Android SDK 的 aapt2（在 PATH 里），或 Python 包 androguard。

用法：app_labels.py -s <序列号> [-o labels.json] [包名 ...]
不给包名时读取全部第三方应用。
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def adb(serial: str, *args: str) -> str:
    return subprocess.run(["adb", "-s", serial, *args], capture_output=True, text=True, stdin=subprocess.DEVNULL).stdout


def label_aapt2(apk: Path) -> str:
    out = subprocess.run(["aapt2", "dump", "badging", str(apk)], capture_output=True, text=True).stdout
    for key in ("application-label-zh-CN:", "application-label-zh:", "application-label:"):
        m = re.search(re.escape(key) + r"'([^']*)'", out)
        if m:
            return m.group(1)
    return ""


def label_androguard(apk: Path) -> str:
    try:
        from loguru import logger  # androguard 的日志库，静音
        logger.remove()
    except Exception:
        pass
    from androguard.core.apk import APK
    return APK(str(apk)).get_app_name() or ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-s", "--serial", required=True)
    ap.add_argument("-o", "--out", default="labels.json")
    ap.add_argument("packages", nargs="*")
    a = ap.parse_args()

    if shutil.which("aapt2"):
        reader = label_aapt2
    else:
        try:
            import androguard  # noqa: F401
            reader = label_androguard
        except ImportError:
            sys.exit("需要 aapt2 或 androguard（pip install androguard）其中之一。")

    pkgs = a.packages or [l.split(":", 1)[1].split()[0] for l in adb(a.serial, "shell", "pm", "list", "packages", "-3").splitlines() if l.startswith("package:")]
    labels = {}
    with tempfile.TemporaryDirectory() as tmp:
        for p in pkgs:
            paths = [l.split(":", 1)[1].strip() for l in adb(a.serial, "shell", "pm", "path", p).splitlines() if l.startswith("package:")]
            base = next((x for x in paths if x.endswith("base.apk")), paths[0] if paths else "")
            if not base:
                continue
            dest = Path(tmp) / f"{p}.apk"
            adb(a.serial, "pull", base, str(dest))
            try:
                labels[p] = reader(dest)
            except Exception as e:  # 个别 APK 解析失败时跳过
                labels[p] = ""
                print(f"{p}: 读取失败 {e}", file=sys.stderr)
            dest.unlink(missing_ok=True)
            print(f"{p}\t{labels[p]}")
    Path(a.out).write_text(json.dumps(labels, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
