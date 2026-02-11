import concurrent.futures
import os
import time

import google.generativeai as genai
from PIL import Image

# --- 配置 ---
KEY_FILE = "gemini_api_key.txt"
INPUT_DIR = "pages"
OUTPUT_DIR = "test_ultra_max_efficiency"

# 利用可能なモデル（Flash系統をメインに分散）
MODELS = [
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-001",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash-exp",  # 試験運用版も含める
]

PROMPT = """
明治時代の統計表をMarkdown形式で抽出してください。
旧字体、単位、コンマの位置を正確に維持。表のみ出力。
"""


def load_key():
    with open(KEY_FILE, "r") as f:
        return f.read().strip()


def process_node(task):
    img_path, out_path, model_name, p_num = task
    print(f"-> STARTing Page {p_num} on {model_name}")
    api_key = load_key()
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)

    start = time.time()
    try:
        img = Image.open(img_path)
        img.thumbnail((2048, 2048))

        # モデルごとのクォータに配慮しつつ実行
        response = model.generate_content([PROMPT, img])

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(response.text)

        dur = time.time() - start
        print(f"<- DONE Page {p_num} using {model_name} in {dur:.1f}s")
        return True
    except Exception as e:
        print(f"!! FAIL Page {p_num} on {model_name}: {str(e)[:100]}")
        return False


def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # 6並列で小テスト (P30-P35)
    target_pages = [f"{i:03}" for i in range(30, 36)]
    tasks = []
    for i, p_num in enumerate(target_pages):
        img_path = os.path.join(INPUT_DIR, f"page_{p_num}.png")
        out_path = os.path.join(OUTPUT_DIR, f"page_{p_num}.md")
        model_name = MODELS[i % len(MODELS)]
        tasks.append((img_path, out_path, model_name, p_num))

    print(
        f"--- Launching Parallel Efficiency Test ({len(tasks)} parallel nodes) ---"
    )
    start = time.time()

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=len(tasks)
    ) as executor:
        executor.map(process_node, tasks)

    print(f"--- Finished in {time.time() - start:.2f}s ---")


if __name__ == "__main__":
    main()
