import os
import json
import subprocess

def git_ls_files(user, repo, branch):
    files = subprocess.check_output(["git", "ls-files"]).decode().splitlines()
    return [
      {
        "path": f,
        "raw": f"https://raw.githubusercontent.com/HirakuArai/vpm-ariade/main/{f}"
      } for f in files
    ]

user = "HirakuArai"
repo = "vpm-ariade"
branch = "main"

index = {
  "generated_at": os.popen("date -u +%Y-%m-%dT%H:%M:%SZ").read().strip(),
  "files": git_ls_files(user, repo, branch)
}
os.makedirs("public", exist_ok=True)
with open("public/all_files_index.json", "w") as fp:
    json.dump(index, fp, ensure_ascii=False, indent=2)
