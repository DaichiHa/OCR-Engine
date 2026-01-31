
import os
import glob
import time
import google.generativeai as genai
from PIL import Image

# --- 設定 ---
# APIキーは `gemini_api_key.txt` から読み込みます
KEY_FILE = "gemini_api_key.txt"
INPUT_DIR = "pages"  # 元画像（補正なしの方がGeminiは読みやすい場合があります）
OUTPUT_DIR = "intermediate_md_gemini"

# プロンプト（Geminiへの指示）
PROMPT = """
この画像は1900年代初頭（明治時代）の「日本帝國港灣統計」の統計表です。
この画像を解析し、正確なMarkdown形式の表に変換してください。

【出力ルール】
1. 表の構造（行列）を維持してください。
2. 漢字は可能な限り正確に再現してください（誤字脱字に注意）。
3. 数字はコンマを含めて正確に抽出してください。
4. 空欄やハイフン（―）は、その通りに記載するか、空白セルにしてください。
5. 出力はMarkdownの表部分のみとしてください。前後の説明テキストは不要です。
"""

def load_key():
    if not os.path.exists(KEY_FILE):
        return None
    with open(KEY_FILE, "r") as f:
        return f.read().strip()

def process_page(model, image_path, page_num):
    print(f"Processing Page {page_num} using Gemini (Stable mode)...")
    max_retries = 5
    base_delay = 65 # クォータ制限は通常60秒なので、余裕を持って65秒
    
    for attempt in range(max_retries):
        try:
            img = Image.open(image_path)
            # 安定性を高めるため画像をリサイズ（Geminiの認識力を落とさずトークン節約）
            img.thumbnail((2048, 2048)) 
            
            response = model.generate_content([PROMPT, img])
            return response.text
        except Exception as e:
            err_str = str(e)
            if "429" in err_str:
                wait_time = base_delay * (attempt + 1)
                print(f"Quota exceeded. Cooling down for {wait_time}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
            elif "500" in err_str or "503" in err_str:
                print(f"Server error. Waiting 10s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(10)
            else:
                return f"Error: {err_str}"
    
    return "Error: Maximum retries exceeded."

def main():
    api_key = load_key()
    if not api_key:
        print(f"Error: {KEY_FILE} Not found.")
        return
    
    genai.configure(api_key=api_key)
    # Flashが制限されているため、Proモデルを試す
    model_name = 'gemini-2.5-pro'
    print(f"Using model: {model_name}")
    model = genai.GenerativeModel(model_name) 

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    files = sorted(glob.glob(os.path.join(INPUT_DIR, "page_*.png")))
    
    # Page 8 から開始
    target_files = [f for f in files if int(os.path.basename(f).split('_')[-1].split('.')[0]) >= 8]

    for file_path in target_files:
        filename = os.path.basename(file_path)
        page_num = filename.replace("page_", "").replace(".png", "")
        
        out_path = os.path.join(OUTPUT_DIR, f"page_{page_num}.md")
        
        if os.path.exists(out_path) and os.path.getsize(out_path) > 100:
            print(f"Skipping {filename}")
            continue

        result = process_page(model, file_path, page_num)
        
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(result)
        
        if "Error" not in result:
            print(f"Page {page_num} Success. Cooling down for 10s to stay safe...")
            time.sleep(10) # 成功後も10秒待機
        else:
            print(f"Page {page_num} Failed: {result}")

    print("Processing complete.")

if __name__ == "__main__":
    main()
