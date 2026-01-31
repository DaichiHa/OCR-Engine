
import os
import glob
import time
import google.generativeai as genai
from PIL import Image

# --- 設定 ---
KEY_FILE = "gemini_api_key.txt"
INPUT_DIR = "pages"
OUTPUT_DIR = "test_stable_interval"
INTERVAL = 30 # 30秒のインターバル

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

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    api_key = load_key()
    genai.configure(api_key=api_key)
    
    # モデルは最も安定している3-flash-previewを使用
    model = genai.GenerativeModel('gemini-3-flash-preview')

    # テスト対象ページ (P21-P23)
    test_pages = ["021", "022", "023"]
    
    print(f"--- Stable Interval Test (Interval: {INTERVAL}s) ---")
    start_all = time.time()

    for p_num in test_pages:
        img_path = os.path.join(INPUT_DIR, f"page_{p_num}.png")
        out_path = os.path.join(OUTPUT_DIR, f"page_{p_num}.md")
        
        print(f"[Start] Page {p_num} at {time.strftime('%H:%M:%S')}")
        
        try:
            img = Image.open(img_path)
            img.thumbnail((2048, 2048))
            
            response = model.generate_content([PROMPT, img])
            
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            
            print(f"[Done]  Page {p_num} Success.")
        except Exception as e:
            print(f"[Error] Page {p_num}: {e}")
        
        print(f"[Wait]  Sleeping for {INTERVAL}s cooldown...")
        time.sleep(INTERVAL)

    print(f"--- Test Finished in {time.time() - start_all:.2f}s ---")

if __name__ == "__main__":
    main()
