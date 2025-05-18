# core/git_ops.py – Git utilities for Kai
"""
▶ 更新概要
* conversations/*.md → conversations/*.json へ完全移行
* check_unprocessed_logs() / push_all_important_files() の glob 修正
* append 用のラッパー commit_and_push_log() を追加（1 会話1 push）

Kai Bot が安全に git pull / add / commit / push を行うユーティリティをまとめる。
既存 capability ID などは温存。
"""
from __future__ import annotations

import json
import os
import subprocess, sys
from pathlib import Path
from core.capabilities_registry import kai_capability
from core.snapshot_utils import regenerate_master_snapshot

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------
PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
CONV_DIR: Path = PROJECT_ROOT / "conversations"
FLAG_PATH: Path = PROJECT_ROOT / "check_flags" / "processed_logs.json"

# GitHub Personal Access Token (環境変数に設定)
github_token: str = os.getenv("GITHUB_TOKEN", "")

# ---------------------------------------------------------------------------
# Git Pull – セーフモード
# ---------------------------------------------------------------------------
@kai_capability(
    id="safe_pull",
    name="リモートリポジトリを最新化",
    description="安全な方法でリモートリポジトリから変更を取得（git pull）します。",
    requires_confirm=True,
)
def try_git_pull_safe() -> None:
    """安全に git pull --rebase する。"""
    try:
        subprocess.run(["git", "stash", "--include-untracked"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "stash", "pop"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ Git pull 完了", flush=True)
        regenerate_master_snapshot()
    except subprocess.CalledProcessError as e:
        print("❌ Git pull 失敗:", e, flush=True)

# ---------------------------------------------------------------------------
# Git Commit & Push for SINGLE FILE
# ---------------------------------------------------------------------------
@kai_capability(
    id="git_commit",
    name="Git コミット & プッシュ",
    description="承認済み変更を git add / commit / push でリポジトリに反映する。",
    requires_confirm=True,
)
def try_git_commit(file_path: str) -> None:
    """指定ファイルを add → commit → push する汎用関数"""
    full_path = Path(file_path).resolve()
    if not full_path.exists():
        print(f"❌ ファイルが存在しません: {full_path}", flush=True)
        return

    print(f" コミット対象ファイル: {full_path}", flush=True)

    subprocess.run(["git", "config", "--global", "user.name", "Kai Bot"], check=True)
    subprocess.run(["git", "config", "--global", "user.email", "kai@example.com"], check=True)

    result = subprocess.run(["git", "add", str(full_path)], capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ git add エラー:", result.stderr, flush=True)
        return

    regenerate_master_snapshot()

    subprocess.run(["git", "commit", "-m", f"Update {full_path.name}"], check=True)
    subprocess.run(["git", "push", f"https://{github_token}@github.com/HirakuArai/vpm-ariade.git"], check=True)

# ---------------------------------------------------------------------------
# 会話ログ 1 ファイルを即時 push（新規）
# ---------------------------------------------------------------------------

def commit_and_push_log(log_path: str) -> None:
    """JSON 会話ログファイルを 1 会話ごとに即 push するヘルパ"""
    try_git_commit(log_path)

# ---------------------------------------------------------------------------
# 未処理ログチェック (JSON 版)
# ---------------------------------------------------------------------------

@kai_capability(
    id="check_unprocessed_logs",
    name="未処理ログのチェック",
    description="Kaiは、関数'check_unprocessed_logs'を通じて未処理のログをチェックする能力を有します。これにより、追跡されていない変更や問題がある場合にはすぐに識別され、対応が可能となります。",
    requires_confirm=False,
    enabled=True,
)
def check_unprocessed_logs() -> None:
    print(" check_unprocessed_logs() 開始", flush=True)
    try:
        flags: dict[str, str] = {}
        if FLAG_PATH.exists():
            flags = json.loads(FLAG_PATH.read_text(encoding="utf-8"))

        files = sorted(f.name for f in CONV_DIR.glob("conversation_*.json"))
        updated = False

        for file in files:
            if file not in flags:
                print(" 未処理ログ:", file, flush=True)
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

# ---------------------------------------------------------------------------
# 重要ファイル一括 push (glob パターン更新)
# ---------------------------------------------------------------------------

@kai_capability(
    id="push_all_files",
    name="重要ファイル全体をGit Push",
    description="docs/, core/, scripts/, data/, conversations/, logs/ などの重要ファイルを一括でGit pushします。",
    requires_confirm=True,
)
def push_all_important_files() -> None:
    try:
        subprocess.run(["git", "config", "--global", "user.name", "Kai Bot"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "kai@example.com"], check=True)

        include_paths = [
            "data/*.json",
            "data/structure_snapshot.json",
            "output/*.json",
            "conversations/*.json",  # ← md → json
            "logs/*.log",
            "docs/*.md",
            "core/**/*.py",
            "scripts/*.py",
        ]

        for pattern in include_paths:
            subprocess.run(["git", "add", pattern], check=True)
        subprocess.run(["git", "commit", "-m", "全重要ファイルを一括push"], check=True)
        subprocess.run(["git", "push", f"https://{github_token}@github.com/HirakuArai/vpm-ariade.git"], check=True)
        print("✅ 重要ファイルを全てpushしました", flush=True)
    except subprocess.CalledProcessError as e:
        print("❌ push_all_important_files エラー:", e, flush=True)
