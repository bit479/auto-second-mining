# -*- coding: utf-8 -*-
"""按人工图给 3960-1008 / 0922 指定"精确分簇"（cluster_exact）。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "圈矿参数.json"

SET = {
    "3960-1008": {
        "ring_mode": "clusters",
        "extrude_m": 3.0,
        "cluster_exact": [
            ["P20", "P21", "P22", "P23", "P24", "P25", "P29", "P30", "P31",
             "P32", "P33", "P34", "P35", "P37", "P38", "P40", "P41", "P42",
             "P43", "P44", "P47", "P62", "P63", "P64", "P65", "P66", "P67"],
            ["P48", "P49", "P50", "P51", "P52", "P53", "P54", "P55", "P56",
             "P57", "P58", "P59", "P60", "P61"],
            ["P8", "P10", "P13", "P14", "P15", "P16", "P17", "P18", "P19"],
            ["P36", "P45", "P46"],
        ],
        "_说明": "按人工图指定的 4 个大簇（791/370/223/119 m² 那四块）",
    },
    "3960-0922": {
        "ring_mode": "clusters",
        "extrude_m": 4.0,
        "cluster_exact": [
            ["P44", "P46", "P47", "P51", "P52", "P53", "P54", "P55", "P56",
             "P58", "P59", "P60"],
        ],
        "_说明": "人工图是 1 块（12 孔），按指定并成一簇",
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
