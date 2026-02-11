import os
import time

import google.generativeai as genai
from PIL import Image

# --- 配置 (LIMIT-BREAK MODE) ---
KEY_FILE = "gemini_api_key.txt"
# 軽量化済み画像ではなく、あえて「原典の最高画質」を分割して使用
INPUT_DIR = "pages"
OUTPUT_DIR = "test_limit_break"
TARGET_PAGE = "page_008.png"

# 【限界突破・分割解析プロンプト】
# AIの抽象化能力を抑え、物理的な転写に全パラメータを集中させる
LIMIT_BREAK_PROMPT = """
[絶対指令: 暗黒転写モード]
あなたは100年前のインクの跡を1ドットの狂いもなくデジタル信号に変換する高精度スキャナーです。
以下の「禁忌」を厳守し、目の前の画像のみをMarkdown化せよ。

[禁忌事項]
1. 現代語への翻訳、要約、挨拶は「汚染」とみなし一切禁止。
2. 漢字の字体修正（新字体への変換）は「情報破壊」であり、絶対に原典の字体（舊字・異體字）を維持せよ。
3. 数値のカンマ、単位（噸、石、斤、圓）の欠落は「致命的バグ」とみなす。
4. 表の構造が複雑な場合、セルの結合を模倣せず、最小単位のグリッドでMarkdownテーブルを構築せよ。

[出力目標]
人間が読むための文書ではなく、100年後の歴史家が解析するための「完全なる原典の複製データ」を出力せよ。
"""


def load_key():
    with open(KEY_FILE, "r") as f:
        return f.read().strip()


def process_limit_break():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    genai.configure(api_key=load_key())
    model = genai.GenerativeModel("gemini-2.0-flash-001")  # 視覚最強モデル

    img_path = os.path.join(INPUT_DIR, TARGET_PAGE)
    img = Image.open(img_path)
    width, height = img.size

    # --- 限界突破手法 1: タイルスキャン (上下分割) ---
    # 全体だと潰れる文字も、分割することでAIの視界内で巨大化する
    print(f"Starting Tile-Scan for {TARGET_PAGE}...")

    # 上半分
    upper_box = (0, 0, width, height // 2)
    upper_img = img.crop(upper_box)

    # 下半分
    lower_box = (0, height // 2, width, height)
    lower_img = img.crop(lower_box)

    results = []

    for i, part in enumerate([upper_img, lower_img]):
        part_name = "Upper" if i == 0 else "Lower"
        print(f"Scanning {part_name} half...")

        # 429回避のためのリトライ
        success = False
        while not success:
            try:
                # 分割した各断片を個別に最高解像度で認識
                response = model.generate_content([LIMIT_BREAK_PROMPT, part])
                results.append(response.text)
                success = True
                print(f"Success: {part_name} segment scanned.")
                time.sleep(10)  # セグメント間は短く冷却
            except Exception:
                print("Quota Hit during segment scan. Waiting 60s...")
                time.sleep(60)

    # 論理的結合
    final_output = "\n\n".join(results)
    out_path = os.path.join(OUTPUT_DIR, TARGET_PAGE.replace(".png", ".md"))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(final_output)

    print(f"--- Limit-Break Test Complete: {out_path} ---")


if __name__ == "__main__":
    process_limit_break()
