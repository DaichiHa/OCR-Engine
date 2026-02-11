import os
import time

import google.generativeai as genai
from PIL import Image

# --- 配置 (ULTRA-Precision & Adaptive PDCA) ---
KEY_FILE = "gemini_api_key.txt"
INPUT_DIR = "pages"
OUTPUT_DIR = "intermediate_md_ultra_final"

# 15秒をベースにしつつ、エラー時はAPIの指示に従う
BASE_INTERVAL = 15
MAX_WORKERS = 1

# 【超・抽出特化型プロンプト】 - 挨拶・要約を一切排除し、データの正確性のみを追求
ULTRA_EXTRACTION_PROMPT = """
あなたは歴史的統計資料のデジタル化専門プログラムです。
画像内の情報を、以下の『絶対規則』に従って100%正確に書き起こしてください。

[絶対規則]
1. 思考・要約・挨拶は一切不要。出力はMarkdown形式の書き起こしのみ。
2. 表形式は1マスもズラさずMarkdownテーブルで再現すること。
3. 漢字はすべて原典のまま（旧字体・異体字を維持。例：港灣、價額、數量、噸、圓）。
4. 数値、コンマ（,）、単位（石、斤、噸、圓等）を1文字も漏らさず記載すること。
5. 縦書きの文章は日本語の正しい順序で、助詞（ニ、ヲ、ハ）も正確に再現すること。
6. 不鮮明な箇所は、前後の文脈から最も可能性が高い文字を推測しつつ、「 [?] 」を付記せずに確定させて出力せよ。

[出力目標]
デジタルアーカイブのマスターデータとなる「究極の複製」を作成せよ。
"""


def load_key():
    with open(KEY_FILE, "r") as f:
        return f.read().strip()


def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    api_key = load_key()
    genai.configure(api_key=api_key)
    # 視覚認識能力が最も高い最新モデルを使用
    model = genai.GenerativeModel("gemini-2.0-flash-001")

    # PDCAテスト：P8, P9, P11 (統計表とテキストが混在する重要ページ)
    test_pages = ["page_008.png", "page_009.png", "page_011.png"]

    print(f"--- ULTRA-PRECISION ADAPTIVE TEST (Base: {BASE_INTERVAL}s) ---")
    start_all = time.time()

    for filename in test_pages:
        img_path = os.path.join(INPUT_DIR, filename)
        out_path = os.path.join(OUTPUT_DIR, filename.replace(".png", ".md"))

        print(f"[{time.strftime('%H:%M:%S')}] Target: {filename}...")

        success = False
        retry_delay = BASE_INTERVAL

        while not success:
            try:
                img = Image.open(img_path)
                # 品質維持のためリサイズを最小限に (3072px)
                img.thumbnail((3072, 3072))

                response = model.generate_content([ULTRA_EXTRACTION_PROMPT, img])

                # 品質チェック: 中身が空でないか
                if response.text and len(response.text) > 50:
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(response.text)
                    print(f"Success: {filename} (ULTRA QUALITY)")
                    success = True
                    # 成功後、次のリクエストまでベース秒数待機
                    time.sleep(BASE_INTERVAL)
                else:
                    raise Exception("Incomplete content generated.")

            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "402" in err_str:
                    print(f"Quota Hit. Waiting {retry_delay}s and scaling up...")
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 120)  # 指数バックオフ
                else:
                    print(f"Error: {err_str[:150]}")
                    time.sleep(10)
                    break  # 重大なエラーはスキップ

    print(f"\n--- ULTRA PDCA Test Complete in {time.time() - start_all:.2f}s ---")


if __name__ == "__main__":
    main()
