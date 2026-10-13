# -*- coding: utf-8 -*-
"""按人工图给 3960-0830（7 块）和 0825（9 块）指定精确分簇。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "圈矿参数.json"

SET = {
    "3960-0830": {
        "ring_mode": "clusters",
        "extrude_m": 3.0,
        "cluster_exact": [
            ["FP6", "FP7", "FP12", "FP13", "FP14", "FP15", "FP18",
             "FP20", "FP21", "FP23", "FP24", "FP27"],
            ["FP1", "FP2", "FP9", "FP10", "FP11"],
            ["FP31", "FP33"],
            ["FP32", "FP35", "FP40"],
            ["FP4", "FP5"],
            ["FP3"],
            ["FP16"],
        ],
        "cluster_exclude": ["FP17"],
        "_说明": "按人工图指定的 7 个簇（人工图里那两块 185/13 m² 是扫描出的细三角片，不是块）",
    },
    "3960-0825": {
        "ring_mode": "clusters",
        "extrude_m": 3.0,
        "cluster_exact": [
            ["P2", "P4", "P29", "P30", "P31", "P32", "P35", "P40", "P41"],
            ["P6", "P7", "P10", "P14", "P15", "P16", "P17", "P18", "P20", "P21"],
            ["P5", "P24", "P25", "P26", "P27"],
            ["P48", "P50", "P52", "P53"],
            ["P43", "P44", "P46"],
            ["P47", "P51"],
            ["P1", "P42", "P45"],
            ["P36", "P37"],
            ["P49"],
        ],
        "_说明": "按人工图指定的 9 个簇（逐块对账得来）",
    },
}


def main() -> None:
    d = json.loads(P.read_text(encoding="utf-8"))
    b = d.setdefault("blasts", {})
    for k, v in SET.items():
        e = b.setdefault(k, {})
        e.pop("cluster_same", None)
        e.pop("cluster_solo", None)
        e.update(v)
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print("已写入：", list(SET))


if __name__ == "__main__":
    main()
