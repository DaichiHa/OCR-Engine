
import os
import glob
import time
import google.generativeai as genai
from PIL import Image

# --- OODA / PDCA Test Configuration ---
KEY_FILE = "gemini_api_key.txt"
INPUT_DIR = "pages"
OUTPUT_DIR = "intermediate_md_ultra_final"
INTERVAL = 15 # User requested 15s interval
MAX_WORKERS = 1 # Single thread as requested

MODELS = ["gemini-2.0-flash"] # Most stable for fast intervals

PROMPT = """
あなたは歴史的な公文書（明治時代の日本の統計資料）をデジタル化する専門家です。
この画像を解析し、以下の指示に従ってMarkdown形式で出力してください。
1. テキストページは旧字体・縦書きの自然な順序を維持。
2. 統計表は行列を正確にMarkdownテーブルで再現。単位・コンマも正確に。
3. Markdown本文のみ。
"""

def load_key():
    with open(KEY_FILE, "r") as f:
        return f.read().strip()

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    api_key = load_key()
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODELS[0])

    # OODA Test Target: Pages 008, 009, 011
    test_pages = ["page_008.png", "page_009.png", "page_011.png"]
    
    print(f"--- OODA/PDCA TEST: 1 Worker, {INTERVAL}s Interval ---")
    start_all = time.time()
    success_count = 0

    for filename in test_pages:
        img_path = os.path.join(INPUT_DIR, filename)
        out_path = os.path.join(OUTPUT_DIR, filename.replace(".png", ".md"))
        
        print(f"[{time.strftime('%H:%M:%S')}] Attempting {filename}...")
        
        try:
            img = Image.open(img_path)
            img.thumbnail((3072, 3072))
            
            response = model.generate_content([PROMPT, img])
            
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            
            print(f"Success: {filename}")
            success_count += 1
        except Exception as e:
            print(f"Fail: {filename} | Error: {e}")
        
        if filename != test_pages[-1]:
            print(f"Waiting {INTERVAL}s interval...")
            time.sleep(INTERVAL)

    print("\n--- Test Results ---")
    print(f"Success: {success_count}/{len(test_pages)}")
    print(f"Total Time: {time.time() - start_all:.2f}s")
    print("--------------------")

if __name__ == "__main__":
    main()
