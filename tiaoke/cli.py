"""命令列煙霧測試：把內建範例事件產成 Excel。

用法：
    python -m tiaoke.cli --list
    python -m tiaoke.cli 瑞文1150223 -o out/瑞文1150223.xlsx
    python -m tiaoke.cli 瑞文1150223 --master 115-1.xlsx
"""

from __future__ import annotations

import argparse
import os
import sys

from . import note_draft, samples
from .builder import build, validate
from .output import run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tiaoke.cli")
    parser.add_argument("event", nargs="?", help="範例事件名稱")
    parser.add_argument("-o", "--out", help="另存新檔路徑")
    parser.add_argument("--master", help="寫入總表路徑")
    parser.add_argument("--list", action="store_true", help="列出可用範例")
    parser.add_argument("--note", action="store_true", help="印出自動產生的說明草稿")
    args = parser.parse_args(argv)

    if args.list or not args.event:
        print("可用範例：")
        for name in samples.SAMPLES:
            print(f"  - {name}")
        return 0

    try:
        event = samples.get(args.event)
    except KeyError:
        print(f"找不到範例：{args.event}", file=sys.stderr)
        return 2

    problems = validate(event)
    if problems:
        print("驗證訊息：")
        for p in problems:
            print(f"  ! {p}")

    slips = build(event)
    print(f"\n事件：{event.sheet_name}")
    print(f"  假別 {event.leave_type} ／ 假單編號 {event.form_no} ／ 公告 {event.announce_date}")
    print(f"  產生 {sum(1 for s in slips if type(s).__name__ == 'TeacherSlip')} 張教師單、"
          f"{sum(1 for s in slips if type(s).__name__ == 'ClassSlip')} 張班級單")
    for s in slips:
        who = getattr(s, "teacher", None) or getattr(s, "klass", "")
        print(f"    · {type(s).__name__:11s} {who}  ({len(s.rows)} 列)")

    print("\n說明草稿：")
    print(f"  {note_draft.draft(event) or '（無）'}")

    if not args.out and not args.master:
        return 0

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    results = run(
        event,
        to_master=bool(args.master), master_path=args.master or "",
        save_new=bool(args.out), dest_path=args.out or "",
    )
    print()
    rc = 0
    for r in results:
        if r.ok:
            extra = "（覆蓋既有工作表）" if r.replaced_sheet else ""
            print(f"  ✓ {r.target}: {r.path} {extra}")
        else:
            print(f"  ✗ {r.target}: {r.error}", file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
