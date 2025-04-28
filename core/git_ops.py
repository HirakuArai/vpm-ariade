# core/git_ops.py
import os, subprocess, json, sys
from pathlib import Path

from core.capabilities_registry import kai_capability

# プロジェクト直下を基点にパスを計算
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONV_DIR = PROJECT_ROOT / "conversations"
FLAG_PATH = PROJECT_ROOT / "check_flags" / "processed_logs.json"

github_token = os.getenv("GITHUB_TOKEN") or ""

# ── Git: pull
@kai_capability(
    id="safe_pull",
    name="リモートリポジトリを最新化",
    description="安全な方法でリモートリポジトリから変更を取得（git pull）します。",
    requires_confirm=True
)

def try_git_pull_safe():
    try:
        subprocess.run(["git", "stash", "--include-untracked"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "stash", "pop"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ Git pull 完了", flush=True)
    except subprocess.CalledProcessError as e:
        print("❌ Git pull 失敗:", e, flush=True)

# ── Git: commit & push
@kai_capability(
    id="git_commit",
    name="Git コミット & プッシュ",
    description="承認済み変更を git add / commit / push でリポジトリに反映する。",
    requires_confirm=True
)

def try_git_commit(file_path: str):
    if not github_token:
        return
    subprocess.run(["git", "config", "--global", "user.name", "Kai Bot"], check=True)
    subprocess.run(["git", "config", "--global", "user.email", "kai@example.com"], check=True)
    subprocess.run(["git", "add", file_path], check=True)
    subprocess.run(["git", "commit", "-m", f"Update {Path(file_path).name}"], check=True)
    subprocess.run(
        ["git", "push",
         f"https://{github_token}@github.com/HirakuArai/vpm-ariade.git"],
        check=True
    )

# ── 会話ログの確認
def check_unprocessed_logs():
    print("🧪 check_unprocessed_logs() 開始", flush=True)
    try:
        flags = {}
        if FLAG_PATH.exists():
            flags = json.loads(FLAG_PATH.read_text(encoding="utf-8"))

        files = sorted(f.name for f in CONV_DIR.glob("conversation_*.md"))
        updated = False
        for file in files:
            if file not in flags:
                print("🟡 未処理ログ:", file, flush=True)
                flags[file] = "checked"
                updated = True

        if updated:
            FLAG_PATH.parent.mkdir(parents=True, exist_ok=True)
            FLAG_PATH.write_text(json.dumps(flags, ensure_ascii=False, indent=2), encoding="utf-8")
            try_git_commit(str(FLAG_PATH))
        else:
            print("✅ すべてのログが処理済みです", flush=True)
    except Exception as e:
        print("❌ check_unprocessed_logs エラー:", e, flush=True)
