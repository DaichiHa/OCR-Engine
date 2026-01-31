
import os
import time
import google.generativeai as genai
from PIL import Image

# --- 設定 ---
KEY_FILE = "gemini_api_key.txt"
INPUT_IMAGE = "pages/page_010.png"
OUTPUT_DIR = "page_010_split_results"

PROMPT = """
この画像は明治時代の統計表の一部です。
Markdown形式の表として抽出してください。
ヘッダーが欠けている場合は、前後の文脈から推測するか、可能な範囲で作成してください。
説明は不要です。表のみ出力してください。
"""

def load_key():
    with open(KEY_FILE, "r") as f:
        return f.read().strip()

def split_and_process():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    api_key = load_key()
    genai.configure(api_key=api_key)
    # 2.0-flash がダメなら 1.5-flash または pro を試す
    model = genai.GenerativeModel('gemini-2.0-flash')

    img = Image.open(INPUT_IMAGE)
    width, height = img.size
    
    # 3分割にする
    parts = 3
    h_step = height // parts
    
    results = []
    
    for i in range(parts):
        top = i * h_step
        bottom = (i + 1) * h_step if i < parts - 1 else height
        box = (0, top, width, bottom)
        chunk = img.crop(box)
        chunk_path = os.path.join(OUTPUT_DIR, f"chunk_{i}.png")
        chunk.save(chunk_path)
        
        print(f"Processing Chunk {i}...")
        
        # リトライ処理
        processed = False
        for attempt in range(3):
            try:
                # 非常に小さい画像にリサイズしてクォータ節約
                temp_chunk = chunk.copy()
                temp_chunk.thumbnail((1600, 1600))
                
                response = model.generate_content([PROMPT, temp_chunk])
                results.append(response.text)
                processed = True
                print(f"Chunk {i} Success.")
                break
            except Exception as e:
                print(f"Chunk {i} Error: {e}. Waiting 30s...")
                time.sleep(30)
        
        if not processed:
            results.append(f"Chunk {i} Failed after retries.")
        
        # 間隔を空ける
        time.sleep(10)

    # 統合
    with open(os.path.join(OUTPUT_DIR, "integrated_page_010.md"), "w", encoding="utf-8") as f:
        f.write("# Page 10 Integrated Result\n\n")
        for res in results:
            f.write(res)
            f.write("\n\n---\n\n")

if __name__ == "__main__":
    split_and_process()
