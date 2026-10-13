# -*- coding: utf-8 -*-
"""按人工图给 3960-0908 指定精确分簇（人工 14 块）。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "圈矿参数.json"

SET = {
    "3960-0908": {
        "ring_mode": "clusters",
        "extrude_m": 3.0,
        "cluster_exact": [
            ["P28", "P29", "P30", "P36", "P37", "P39", "P40", "P44"],
            ["P56", "P60", "P61", "P63"],
            ["P51", "P52", "P54"],
            ["P50", "P66"],
            ["P57", "P58"],
            ["P12", "P13"],
            ["P31"], ["P32"], ["P38"], ["P18"], ["P49"], ["P59"],
            ["P10"], ["P62"],
        ],
        "cluster_exclude": ["P46"],
        "_说明": "按人工图指定的 14 个簇（逐块对账得来，见 _probe/cluster_diff.py）",
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
