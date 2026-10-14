import json, subprocess, urllib.request, urllib.error, urllib.parse
from pathlib import Path
ROOT = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型"
ZIP = Path(r"D:\WK\N CRT\release_v1\second-mining-tool-v1.0.zip")
out = subprocess.run(["git","credential","fill"], input="protocol=https\nhost=github.com\n\n", capture_output=True, text=True, cwd=ROOT).stdout
tok = dict(l.split("=",1) for l in out.splitlines() if "=" in l).get("password","")
def api(url, data=None, method="GET", ctype="application/json"):
    r = urllib.request.Request(url, method=method)
    r.add_header("Authorization","Bearer "+tok); r.add_header("Accept","application/vnd.github+json"); r.add_header("User-Agent","codex")
    body=None
    if data is not None:
        body = data if isinstance(data, bytes) else json.dumps(data).encode()
        r.add_header("Content-Type", ctype)
    try:
        with urllib.request.urlopen(r, body, timeout=180) as resp: return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e: return e.code, {"error": e.read().decode("utf-8","replace")[:200]}
st, rel = api("https://api.github.com/repos/bit479/auto-second-mining/releases/tags/v1.0")
rid = rel["id"]
url = "https://uploads.github.com/repos/bit479/auto-second-mining/releases/%d/assets?name=%s" % (rid, ZIP.name)
st3, res3 = api(url, ZIP.read_bytes(), method="POST", ctype="application/zip")
print("上传 ->", st3, res3.get("name"), res3.get("browser_download_url") or res3.get("error"))
