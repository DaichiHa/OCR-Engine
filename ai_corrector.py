import glob
import os

from openai import OpenAI

# Configuration
INPUT_DIR = "intermediate_md_strong"
OUTPUT_DIR = "intermediate_md_ai"
KEY_FILE = "openai_api_key.txt"


def load_key():
    with open(KEY_FILE, "r") as f:
        return f.read().strip()


def correct_page(client, page_content, page_num):
    prompt = f"""
あなたは歴史的な統計資料の校正エンジニアです。
以下のテキストは、明治時代の「日本帝國港灣統計」をOCRしたものです。
OCRの特性上、漢字の誤認識（例：「束京」→「東京」、「言」→「計」）や、表のレイアウトの乱れがあります。

以下のガイドラインに従って修正してください：
1. 明治時代の地名や用語として自然な漢字に修正してください。
2. 数字の読み取りミスを、表の文脈（合計値など）から推測できる場合は修正してください。
3. Markdownの表形式（|---|---|）を維持、または崩れている場合は修復してください。
4. 元のデータの値を勝手に要約したり削除したりしないでください。
5. 出力は修正後のMarkdownテキストのみを返してください。不要な解説は不要です。

---
対象：Page {page_num}
{page_content}
"""
    try:
        response = client.chat.completions.create(
            _model="gpt-4o-mini",
            _messages=[
                {
                    "role": "system",
                    "content": "You are a professional historical data editor.",
                },
                {"role": "user", "content": prompt},
            ],
            _temperature=0,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error on Page {page_num}: {str(e)}"


def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    api_key = load_key()
    if not api_key.startswith("sk-"):
        print("Error: Invalid OpenAI API key format in openai_api_key.txt. Should start with 'sk-'.")
        return

    client = OpenAI(api_key=api_key)

    files = sorted(glob.glob(os.path.join(INPUT_DIR, "page_*.md")))

    print(f"Starting AI correction for {len(files)} pages using GPT-4o-mini...")

    for file_path in files:
        filename = os.path.basename(file_path)
        page_num = filename.replace("page_", "").replace(".md", "")

        # Skip if already exists
        out_path = os.path.join(OUTPUT_DIR, filename)
        if os.path.exists(out_path):
            print(f"Skipping Page {page_num} (already corrected)")
            continue

        print(f"Processing Page {page_num}...", end="\r")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        corrected = correct_page(client, content, page_num)

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(corrected)

        print(f"Page {page_num} corrected successfully.   ")


if __name__ == "__main__":
    main()
