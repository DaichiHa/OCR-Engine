import concurrent.futures
import os
import time

import google.generativeai as genai
from PIL import Image

# --- 設定 ---
KEY_FILE = "gemini_api_key.txt"
INPUT_DIR = "pages"
OUTPUT_DIR = "test_ultra_hyper_parallel"  # 極限並列テスト用
MAX_WORKERS = 8  # 並列数を8に引き上げ

# 利用可能なモデルプール (利用可能なものから優先的に使用)
# 複数のモデル、複数のバージョンを混ぜてクォータの合算を狙う
MODEL_POOL = [
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-2.0-flash-001",
    "gemini-2.0-flash",
]

PROMPT = """
あなたは歴史的な公文書（明治時代の日本の統計資料）をデジタル化する専門家です。
この画像を解析し、以下の指示に従ってMarkdown形式で出力してください。

1. **テキストページ（序文・緒言など）**:
   - 縦書きの文章を、日本語の自然な順序で正しく書き起こしてください。
   - 旧字体や助詞（ニ、ヲ、ハ）もそのまま再現してください。

2. **統計表ページ**:
   - 表の行列を1マスもずらさずにMarkdownテーブルで再現してください。
   - 単位（石、噸、圓、斤など）を正確に含めてください。
   - コンマ（,）の位置も正確に再現してください。

3. **出力形式**:
   - Markdownの本文のみ。
"""


def load_key():
    with open(KEY_FILE, "r") as f:
        return f.read().strip()


def process_page_hyper(task):
    image_path, out_path, model_name, page_num = task
    print(f"[Start] Page {page_num} | Model: {model_name}")

    genai.configure(api_key=load_key())
    model = genai.GenerativeModel(model_name)

    start_time = time.time()
    max_retries = 3

    for attempt in range(max_retries):
        try:
            img = Image.open(image_path)
            # 2048pxはGeminiが最も効率的に、かつ高精度に読める解像度
            img.thumbnail((2048, 2048))

            response = model.generate_content([PROMPT, img])

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(response.text)

            dur = time.time() - start_time
            print(f"[Done]  Page {page_num} | {dur:.1f}s | {model_name}")
            return True
        except Exception as e:
            if "429" in str(e):
                # モデルごとのクォータに当たった場合は少し長めに待機
                wait = 45  # 429時は固定で45秒（リセットを待つ）
                print(f"[Limit] Page {page_num} on {model_name} (429). Waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"[Error] Page {page_num} on {model_name}: {e}")
                time.sleep(5)
    return False


def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # テスト対象ページ (P13-P20の8ページ分、並列最大効率を検証)
    pages_to_test = [f"{i:03}" for i in range(13, 21)]
    tasks = []

    for i, p_num in enumerate(pages_to_test):
        img_path = os.path.join(INPUT_DIR, f"page_{p_num}.png")
        out_path = os.path.join(OUTPUT_DIR, f"page_{p_num}.md")
        # モデルプールから順番に割り当て
        model_name = MODEL_POOL[i % len(MODEL_POOL)]
        tasks.append((img_path, out_path, model_name, p_num))

    print(f"Starting Hyper-Parallel Test (Workers: {MAX_WORKERS}, Models: {len(MODEL_POOL)})")
    overall_start = time.time()

    # 並列実行
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        executor.map(process_page_hyper, tasks)

    overall_dur = time.time() - overall_start
    print("\n--- Hyper Test Complete ---")
    print(f"Total Pages: {len(pages_to_test)}")
    print(f"Total Time:  {overall_dur:.2f}s")
    print(f"Efficiency:  {overall_dur/len(pages_to_test):.2f} s/page")


if __name__ == "__main__":
    main()
