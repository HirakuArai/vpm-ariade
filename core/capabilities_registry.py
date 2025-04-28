# core/capabilities_registry.py

def kai_capability(id, name, description, requires_confirm=False, enabled=True):
    """
    Kai の能力情報を関数に付与するためのデコレータ。
    本来の関数の動作には一切影響を与えず、安全にメタデータだけ付与する。
    """
    def decorator(fn):
        fn._kai_capability = {
            "id": id,
            "name": name,
            "description": description,
            "requires_confirm": requires_confirm,
            "enabled": enabled
        }
        return fn
    return decorator
