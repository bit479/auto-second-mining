# -*- coding: utf-8 -*-
"""按人工图给 3960-1009 指定精确分簇（人工 4 块）。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "圈矿参数.json"

SET = {
    "3960-1009": {
        "ring_mode": "clusters",
        "extrude_m": 3.0,
        "cluster_exact": [
            ["P38", "P39", "P40", "P41", "P42", "P45"],
            ["P3", "P4"],
            ["P5", "P6"],
            ["P7", "P8"],
        ],
        "_说明": "按人工图指定的 4 个簇（我们原来把 P5/P6 拆成两块了）",
    },
}


def main() -> None:
    d = json.loads(P.read_text(encoding="utf-8"))
    b = d.setdefault("blasts", {})
    for k, v in SET.items():
        b.setdefault(k, {}).update(v)
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print("已写入：", list(SET))


if __name__ == "__main__":
    main()
