#!/usr/bin/env python3
"""UTF-8 安全的 STATUS.md 追加器(T1-W5)。

ssh echo 中文追加会乱码(2026-09-26 踩过),一律经本工具写:

    python3 status_append.py "HH:MM | T1 | <单元> | 状态 | 备注"

时间戳缺省取当前时刻,格式与既有 STATUS.md 行保持一致。
"""
import io
import sys
from datetime import datetime
from pathlib import Path

STATUS = Path.home() / "sitl_sim" / "STATUS.md"


def main() -> int:
    if len(sys.argv) < 2:
        print(f"用法: {sys.argv[0]} \"<一行状态>\"", file=sys.stderr)
        return 2
    line = " ".join(sys.argv[1:])
    if not line[:2].isdigit() or ":" not in line[:5]:
        line = datetime.now().strftime("%H:%M | ") + line
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    with io.open(STATUS, "a", encoding="utf-8") as f:
        f.write(line.rstrip("\n") + "\n")
    print(f"appended: {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
