# -*- coding: utf-8 -*-
# 打 tag v1.0 + 在 GitHub 上发 Release v1.0 并附 zip 资产（凭据取自 git 凭据助手，不打印）。
# 用法: python _probe/_publish_v1.py [--dry-run]
from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "bit479/auto-second-mining"
TAG = "v1.0"
ZIP = Path(r"D:\WK\N CRT\release_v1\二次圈矿工具_v1.0.zip")
NOTES = Path(__file__).resolve().with_name("release_notes_v1.md")
DRY = "--dry-run" in sys.argv


def token() -> str:
    out = subprocess.run(["git", "credential", "fill"],
                         input="protocol=https\nhost=github.com\n\n",
                         capture_output=True, text=True, cwd=str(ROOT)).stdout
    d = dict(l.split("=", 1) for l in out.splitlines() if "=" in l)
    return d.get("password", "")


def api(url: str, tok: str, data=None, method="GET", ctype="application/json"):
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", "Bearer " + tok)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "codex-publish")
    body = None
    if data is not None:
        body = data if isinstance(data, bytes) else json.dumps(data).encode("utf-8")
        req.add_header("Content-Type", ctype)
    try:
        with urllib.request.urlopen(req, body, timeout=180) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode("utf-8", "replace")[:400]}


def main() -> int:
    tok = token()
    if not tok:
        print("没取到 GitHub 凭据，无法发 Release。")
        return 2
    print("凭据已取到（账号 bit479；内容不显示）")
    body = NOTES.read_text(encoding="utf-8")

    p = subprocess.run(["git", "tag", "-a", TAG, "-m",
                        "v1.0 首个可用版（17 个炮区验收全绿）"],
                       cwd=str(ROOT), capture_output=True, text=True)
    print("git tag ->", (p.stdout + p.stderr).strip() or "已创建")
    if not DRY:
        p = subprocess.run(["git", "push", "origin", TAG], cwd=str(ROOT),
                           capture_output=True, text=True)
        print("git push tag ->", (p.stdout + p.stderr).strip()[-160:])

    st, res = api("https://api.github.com/repos/%s/releases" % REPO, tok,
                  {"tag_name": TAG, "name": "v1.0 —— 二次圈矿工具（首个可用版）",
                   "body": body, "draft": False, "prerelease": False},
                  method="POST")
    print("建 Release ->", st, res.get("html_url") or str(res.get("error", ""))[:300])
    if st == 422:
        st2, res2 = api("https://api.github.com/repos/%s/releases/tags/%s" % (REPO, TAG), tok)
        print("（该 tag 的 Release 已存在）", st2, res2.get("html_url"))
        res = res2
    rel_id = res.get("id")

    if rel_id and ZIP.exists() and not DRY:
        data = ZIP.read_bytes()
        url = ("https://uploads.github.com/repos/%s/releases/%d/assets?name=%s"
               % (REPO, rel_id, urllib.parse.quote(ZIP.name)))
        st3, res3 = api(url, tok, data, method="POST", ctype="application/zip")
        print("上传资产 %s（%.2f MB）-> %s %s" % (ZIP.name, len(data) / 1048576, st3,
              res3.get("browser_download_url") or str(res3.get("error", ""))[:200]))
    elif not ZIP.exists():
        print("没找到 zip 资产：%s（只发 Release、不附文件）" % ZIP)
    print("完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
