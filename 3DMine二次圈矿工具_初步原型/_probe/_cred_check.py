# -*- coding: utf-8 -*-
# 只检查 git 凭据助手里有没有 GitHub 的推送凭据，不打印凭据本身。
import subprocess

inp = "protocol=https\nhost=github.com\n\n"
out = subprocess.run(["git", "credential", "fill"], input=inp,
                     capture_output=True, text=True).stdout
d = dict(l.split("=", 1) for l in out.splitlines() if "=" in l)
pw = d.get("password", "")
kind = "无"
if pw.startswith("github_pat_"):
    kind = "细粒度 PAT"
elif pw.startswith("ghp_"):
    kind = "经典 PAT"
elif pw:
    kind = "其他凭据（长度 %d）" % len(pw)
print("凭据里的账号:", d.get("username", "(无)"))
print("有没有可用凭据:", "有" if pw else "没有")
print("凭据类型:", kind)
