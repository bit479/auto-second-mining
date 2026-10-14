# -*- coding: utf-8 -*-
# 读一次 GitHub Release 的状态（不打印凭据）
import json
import subprocess
import sys
import urllib.request

ROOT = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型"
TAG = sys.argv[1] if len(sys.argv) > 1 else "v1.0"
out = subprocess.run(["git", "credential", "fill"],
                     input="protocol=https\nhost=github.com\n\n",
                     capture_output=True, text=True, cwd=ROOT).stdout
tok = dict(l.split("=", 1) for l in out.splitlines() if "=" in l).get("password", "")
req = urllib.request.Request(
    "https://api.github.com/repos/bit479/auto-second-mining/releases/tags/" + TAG)
req.add_header("Authorization", "Bearer " + tok)
req.add_header("Accept", "application/vnd.github+json")
req.add_header("User-Agent", "codex")
rel = json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))
print("Release :", rel["name"])
print("页面    :", rel["html_url"])
print("tag     :", rel["tag_name"], " 指向:", rel.get("target_commitish"))
print("说明    :", len(rel.get("body") or ""), "字符")
print("资产    :")
for a in rel.get("assets", []):
    print("   - %s  %.2f MB  %s" % (a["name"], a["size"] / 1048576,
                                   a["browser_download_url"]))
