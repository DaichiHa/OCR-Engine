
import os
import time
import google.generativeai as genai
from PIL import Image

KEY_FILE = "gemini_api_key.txt"
INPUT_DIR = "pages"
OUTPUT_DIR = "test_ultra_results"

PROMPT = """
あなたは歴史的な公文書（明治時代の日本の統計資料）をデジタル化する専門家です。
この画像を解析し、以下の指示に従ってMarkdown形式で出力してください。

1. **テキストページ（序文・緒言など）**:
   - 縦書きの文章を、日本語の自然な順序で正しく書き起こしてください。
   - 旧字体（例：灣、國、實、關）やカタカナ、「ニ」「ヲ」「ハ」などの助詞もそのまま再現してください。

2. **統計表ページ**:
   - 表の行列を1マスもずらさずにMarkdownテーブルで再現してください。
   - 単位（石、噸、圓、斤など）が数字の上に小さく書いてある場合は、数値の後に含めるかヘッダーに含めてください。
   - コンマ（,）の位置も正確に再現してください。
   - 漢字の認識ミス（東京を束京とする等）を文脈から判断して修正してください。

3. **出力形式**:
   - Markdownのテキストのみ。前後の説明は一切不要です。
"""

def load_key():
    with open(KEY_FILE, "r") as f:
        return f.read().strip()

def main():
    api_key = load_key()
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # テスト対象のページ
    test_pages = ["page_001.png", "page_003.png", "page_008.png"]
    
    for filename in test_pages:
        file_path = os.path.join(INPUT_DIR, filename)
        page_num = filename.replace("page_", "").replace(".png", "")
        print(f"Testing Page {page_num}...")
        
        try:
            img = Image.open(file_path)
            response = model.generate_content([PROMPT, img])
            
            out_path = os.path.join(OUTPUT_DIR, f"test_page_{page_num}.md")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"Page {page_num} Success.")
        except Exception as e:
            print(f"Page {page_num} Failed: {e}")
        
        time.sleep(10)

if __name__ == "__main__":
    main()
