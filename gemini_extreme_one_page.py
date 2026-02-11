import os
import time

import google.generativeai as genai
from PIL import Image

# --- 極限・品質重視・単一ページ抽出 (4分割タイル・スキャン) ---
KEY_FILE = "gemini_api_key.txt"
TARGET_PAGE = "page_008.png"
INPUT_DIR = "pages"
OUTPUT_DIR = "extreme_quality_test"

# 【究極の暗黒転写プロンプト】
EXTREME_PROMPT = """
[最終指令: 零欠損デジタル化]
あなたは明治時代の超微細な統計資料をデジタル保存するための、超高性能な転写エンジンです。
今から提示する「画像の一部（断片）」に含まれるすべての情報を、1文字の誤差もなくMarkdown化してください。

[実行ルール]
1. 挨拶・説明は一切不要。
2. 表の構造（罫線）を完璧にMarkdownテーブルへ変換せよ。
3. 漢字：旧字体（港灣、東京、計、國等）を100%維持せよ。
4. 数値：3桁区切りのコンマ、単位（噸、石、斤）を正確に。
5. 推測せず、形状をそのまま記述せよ。不鮮明な箇所は文脈から「もっとも正しい旧字体」を選択せよ。

これは日本の国益に関わる重要なデジタルアーカイブ作業である。一画一字に魂を込めよ。
"""


def load_key():
    with open(KEY_FILE, "r") as f:
        return f.read().strip()


def process_extreme_one_page():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    genai.configure(api_key=load_key())
    # 8Bモデルは制限が非常に緩く、タイル分割と組み合わせれば高精度が期待できる
    model = genai.GenerativeModel("gemini-1.5-flash-8b")

    img_path = os.path.join(INPUT_DIR, TARGET_PAGE)
    img = Image.open(img_path)
    width, height = img.size

    # 4分割 (Top-Left, Top-Right, Bottom-Left, Bottom-Right)
    # これによりAIの視界が4倍に拡大され、微細な数字も鮮明に認識される
    mid_x, mid_y = width // 2, height // 2
    tiles = [
        (0, 0, mid_x, mid_y),  # TL
        (mid_x, 0, width, mid_y),  # TR
        (0, mid_y, mid_x, height),  # BL
        (mid_x, mid_y, width, height),  # BR
    ]
    tile_names = ["Top-Left", "Top-Right", "Bottom-Left", "Bottom-Right"]

    print(f"--- EXTREME QUALITY TEST: {TARGET_PAGE} (4-Tile Scan) ---")
    print("Pre-cooling 60s to ensure API availability...")
    time.sleep(60)

    results = {}
    for i, box in enumerate(tiles):
        name = tile_names[i]
        print(f"[{time.strftime('%H:%M:%S')}] Scanning {name}...")

        tile_img = img.crop(box)

        success = False
        while not success:
            try:
                response = model.generate_content([EXTREME_PROMPT, tile_img])
                results[name] = response.text
                print(f"   -> {name} Success.")
                success = True
                # 次のタイルまで長く休む (APIバケツを貯める)
                print("   Waiting 90s for quota recovery...")
                time.sleep(90)
            except Exception as e:
                print(f"   Quota Lock. Waiting 180s... ({e})")
                time.sleep(180)

    # 4つの断片を一つのMDに統合
    final_path = os.path.join(
        OUTPUT_DIR, f"{TARGET_PAGE.replace('.png', '')}_EXTREME.md"
    )
    with open(final_path, "w", encoding="utf-8") as f:
        f.write(f"# {TARGET_PAGE} EXTREME QUALITY RECONSTRUCTION\n\n")
        for name in tile_names:
            f.write(f"\n--- Section: {name} ---\n\n")
            f.write(results[name])
            f.write("\n")

    print(f"\n--- EXTREME TEST COMPLETE: {final_path} ---")


if __name__ == "__main__":
    process_extreme_one_page()
