from core.markdown_utils import extract_code_from_markdown
from core.code_rewriter import replace_function_in_source
from core.git_ops import try_git_commit
from core.patch_log import log_patch
import os

from core.capabilities_registry import kai_capability

@kai_capability(
    id="apply_patch",
    name="GPT修正提案を適用",
    description="GPTが提案したコード修正案をソースコードに適用します。",
    requires_confirm=True
)

def apply_gpt_patch(markdown_text: str, fn_name: str, source_path: str = "app.py", auto_commit: bool = True) -> bool:
    """
    GPTが返したMarkdown形式の修正提案（markdown_text）からコードブロックを抽出し、
    指定された関数(fn_name)に上書きする。成功時に Git commit も実行。
    """
    code = extract_code_from_markdown(markdown_text)
    if not code:
        print("❌ コードブロックが抽出できませんでした。")
        return False

    success = replace_function_in_source(source_path, fn_name, code)
    if success:
        # ✅ Patch log を記録
        instruction = (
            st.session_state.get("fn_instruction", "") if "st" in globals() else
            f"関数 `{fn_name}` を GPT により自動改修（Kai UIから）"
        )
        log_patch(fn_name=fn_name, user_instruction=instruction, markdown_diff=markdown_text)

        if auto_commit:
            try_git_commit(source_path)
            if os.path.exists("patch_history.json"):
                try_git_commit("patch_history.json")

    return success
