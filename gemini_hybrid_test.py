import os
import time

import google.generativeai as genai

# --- 配置 (HYBRID-ULTRA テスト) ---
KEY_FILE = "gemini_api_key.txt"
DRAFT_DIR = "local_ultra_results"
OUTPUT_DIR = "hybrid_ultra_results"
TARGET_PAGE = "page_008"

# 【ハイブリッド・論理修正プロンプト】
# 画像は送らず、壊れたテキストから「正解」を復元させる
HYBRID_CORRECTION_PROMPT = """
あなたは歴史的統計資料の復元専門家です。
以下は、明治時代の統計表をOCR（光学文字認識）した際の「壊れた下書き」です。
あなたの知識（明治時代の漢字、地名、統計の整合性）を総動員し、これを「ULTRA品質」のMarkdownテーブルへ復元してください。

[復元の手がかり]
- 資料名: 明治三十九年 日本帝國港灣統計 第一表
- 項目: 地方、港灣、郡市町村、汽船（定期・不定期・計）、帆船、和船、合計
- 漢字: 旧字体（港灣、東京、横濱、國、計）を維持。
- コンマ: 数値の3桁区切りを論理的に復元せよ。
- 整合性: 合計欄の数値が、各項目の和として妥当かチェックせよ。

[下書きテキスト]
{draft_text}

[出力]
Markdownテーブルのみを出力せよ。
"""


def load_key():
    with open(KEY_FILE, "r") as f:
        return f.read().strip()


def process_hybrid_ultra():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    genai.configure(api_key=load_key())
    # テキスト処理能力に優れたモデルを使用
    model = genai.GenerativeModel("gemini-2.0-flash")

    draft_path = os.path.join(DRAFT_DIR, f"{TARGET_PAGE}.txt")
    if not os.path.exists(draft_path):
        print(f"Draft not found: {draft_path}")
        return

    with open(draft_path, "r", encoding="utf-8") as f:
        draft_text = f.read()

    print(f"[{time.strftime('%H:%M:%S')}] Hybrid-ULTRA: Refining draft for {TARGET_PAGE}...")

    try:
        # 画像なし、テキストのみのリクエスト（制限が非常に緩い）
        response = model.generate_content(HYBRID_CORRECTION_PROMPT.format(draft_text=draft_text))

        out_path = os.path.join(OUTPUT_DIR, f"{TARGET_PAGE}.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(response.text)

        print(f"--- Hybrid-ULTRA Success: {out_path} ---")
        print("Text-only request completed. This method is 100x more stable against 429 errors.")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    process_hybrid_ultra()
