# -*- coding: utf-8 -*-
"""把 3960-0830 / 1007 的人工分组写进 圈矿参数.json（方案二：分簇人工指定）。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "圈矿参数.json"

SET = {
    "3960-0830": {
        "ring_mode": "clusters",
        "extrude_m": 3.0,
        "cluster_same": [
            ["FP6", "FP7", "FP12", "FP13", "FP14", "FP15", "FP18",
             "FP20", "FP21", "FP23", "FP24", "FP27"],
            ["FP1", "FP2", "FP9", "FP10", "FP11"],
            ["FP31", "FP33"],
            ["FP32", "FP35", "FP40"],
            ["FP4", "FP5"],
        ],
        "cluster_solo": [["FP3"], ["FP16"]],
        "cluster_exclude": ["FP17"],
        "_说明": "按人工图指定的分簇（9 块）；外推 3 m、clusters 模式",
    },
    "3960-1007": {
        "ring_mode": "clusters",
        "extrude_m": 4.0,
        "cluster_same": [["P1", "P2", "P6", "P11", "P12", "P16"]],
        "_说明": "人工图是 1 块（6 孔），按指定并成一簇",
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
