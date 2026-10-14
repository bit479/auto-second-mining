import json, subprocess, urllib.request, urllib.error
ROOT = r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型"
out = subprocess.run(["git","credential","fill"], input="protocol=https\nhost=github.com\n\n", capture_output=True, text=True, cwd=ROOT).stdout
tok = dict(l.split("=",1) for l in out.splitlines() if "=" in l).get("password","")
def api(url, method="GET"):
    r = urllib.request.Request(url, method=method)
    r.add_header("Authorization","Bearer "+tok); r.add_header("Accept","application/vnd.github+json"); r.add_header("User-Agent","codex")
    try:
        with urllib.request.urlopen(r, timeout=60) as resp: return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e: return e.code, {"error": e.read().decode("utf-8","replace")[:200]}
st, rel = api("https://api.github.com/repos/bit479/auto-second-mining/releases/tags/v1.0")
print("release:", st, rel.get("html_url"), "| 资产数:", len(rel.get("assets", [])))
for a in rel.get("assets", []):
    print("  资产 id=%s name=%r 大小=%.2f MB" % (a["id"], a["name"], a["size"]/1048576))
    st2, _ = api("https://api.github.com/repos/bit479/auto-second-mining/releases/assets/%d" % a["id"], method="DELETE")
    print("  删除该资产 ->", st2)
