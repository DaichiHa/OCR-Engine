import os

KYUUJITAI_MAP = {
    "會": "会",
    "舊": "旧",
    "國": "国",
    "圓": "円",
    "廣": "広",
    "豐": "豊",
    "鐵": "鉄",
    "學": "学",
    "號": "号",
    "廳": "庁",
}

DEFAULT_TESSERACT_CONFIG_DIR = os.path.join(os.path.dirname(__file__), "tesseract_config")


def normalize_kyuujitai(text, enabled=True):
    if not enabled:
        return text
    normalized = text
    for old, new in KYUUJITAI_MAP.items():
        normalized = normalized.replace(old, new)
    return normalized


def _format_tesseract_path(path):
    if path and " " in path:
        return f'"{path}"'
    return path


def build_tesseract_config(
    base_config,
    config_dir=None,
    user_words_path=None,
    user_patterns_path=None,
):
    config_parts = [base_config]
    resolved_config_dir = config_dir or DEFAULT_TESSERACT_CONFIG_DIR
    resolved_user_words = user_words_path or os.path.join(resolved_config_dir, "user-words")
    resolved_user_patterns = user_patterns_path or os.path.join(resolved_config_dir, "user-patterns")

    if resolved_user_words and os.path.exists(resolved_user_words):
        config_parts.append(f"--user-words {_format_tesseract_path(resolved_user_words)}")
    if resolved_user_patterns and os.path.exists(resolved_user_patterns):
        config_parts.append(f"--user-patterns {_format_tesseract_path(resolved_user_patterns)}")

    return " ".join(config_parts).strip()
