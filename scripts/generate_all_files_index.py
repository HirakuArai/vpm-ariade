import os, json, subprocess

def git_ls_files():
    files = subprocess.check_output(["git", "ls-files"]).decode().splitlines()
    return [
      {
        "path": f,
        "raw": f"https://raw.githubusercontent.com/${{GITHUB_REPOSITORY}}/${{GITHUB_REF_NAME}}/{f}"
      } for f in files
    ]

index = {
  "generated_at": os.popen("date -u +%Y-%m-%dT%H:%M:%SZ").read().strip(),
  "files": git_ls_files()
}
with open("all_files_index.json", "w") as fp:
    json.dump(index, fp, ensure_ascii=False, indent=2)
