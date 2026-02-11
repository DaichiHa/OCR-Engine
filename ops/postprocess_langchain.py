import argparse
import json
import os
import re
import unicodedata


def basic_cleanup(text, mappings=None):
    # Unicode normalize
    t = unicodedata.normalize("NFKC", text)
    # remove control chars
    t = re.sub(r"[\x00-\x1f\x7f]", "", t)
    # collapse whitespace
    t = re.sub(r"[ \t\u3000]+", " ", t)
    # fix common OCR punctuation
    t = t.replace("。", "。").replace("，", ",")
    t = t.replace("·", ".")
    # remove stray non-CJK letters immediately before digits (e.g. OCR noise like '카59')
    t = re.sub(
        r"([^\u4E00-\u9FFF\u3040-\u30FF\u3130-\u318F\uAC00-\uD7AF\d\w])(?=\d)", "", t
    )
    # apply mapping replacements
    if mappings:
        for k, v in mappings.items():
            t = t.replace(k, v)
    # trim
    t = re.sub(r"\s+\n", "\n", t)
    return t.strip()


def jp_rate2_fix(s):
    import re

    c = re.sub(r"[\s\|\-—_\.]", "", s or "")
    jp = len(re.findall(r"[\u3040-\u30ff\u3400-\u9fff]", c))
    return jp / max(1, len(c))


def noise_rate2_fix(s):
    import re

    c = re.sub(r"[\r\n\t ]", "", s or "")
    non = len(re.findall(r"[^0-9A-Za-z\u3040-\u30ff\u3400-\u9fff,()%\-]", c))
    return non / max(1, len(c))


def run_rule_pipeline(in_path, out_path):
    with open(in_path, "r", encoding="utf-8") as f:
        src = f.read()

    mappings = {
        "哈爾賓": "哈尔滨",
        "哈爾濱": "哈尔滨",
        "支那在留本邦人": "支那在留日本人",
    }

    before = src
    before_jp = jp_rate2_fix(before)
    before_noise = noise_rate2_fix(before)

    cleaned = basic_cleanup(src, mappings=mappings)

    after_jp = jp_rate2_fix(cleaned)
    after_noise = noise_rate2_fix(cleaned)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(cleaned)

    summary = {
        "in": in_path,
        "out": out_path,
        "before_jp_rate2_fix": before_jp,
        "before_noise_rate2_fix": before_noise,
        "after_jp_rate2_fix": after_jp,
        "after_noise_rate2_fix": after_noise,
    }
    print("WROTE", out_path)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument("--out", dest="out_path", required=True)
    ap.add_argument(
        "--use-llm",
        action="store_true",
        help="If set and API key present, attempt LangChain LLM pass",
    )
    args = ap.parse_args()

    # If LLM requested and env var present, attempt to call LangChain/OpenAI
    if (
        args.use_llm
        and os.getenv("OPENAI_API_KEY")
        and os.getenv("USE_LANGCHAIN", "1") != "0"
    ):
        try:
            from langchain import LLMChain, PromptTemplate
            from langchain.llms import OpenAI

            with open(args.in_path, "r", encoding="utf-8") as f:
                src = f.read()
            prompt = PromptTemplate(
                input_variables=["text"],
                template=(
                    "You are a specialist in correcting OCR output from Showa-era Japanese statistical tables. "
                    "Correct OCR errors, normalize old kanji to modern equivalents, fix numbers and punctuation, and preserve layout. "
                    "Return only the corrected text.\n\nInput:\n{text}\n\nCorrected:"
                ),
            )
            llm = OpenAI(temperature=0)
            chain = LLMChain(llm=llm, prompt=prompt)
            # chunk large text
            chunk_size = 4000
            parts = [src[i : i + chunk_size] for i in range(0, len(src), chunk_size)]
            out_parts = []
            for p in parts:
                res = chain.run(text=p)
                out_parts.append(res)
            corrected = "\n".join(out_parts)
            with open(args.out_path, "w", encoding="utf-8") as f:
                f.write(corrected)
            print("WROTE (LLM)", args.out_path)
            return
        except Exception as e:
            print("LLM pass failed, falling back to rule-based:", e)

    run_rule_pipeline(args.in_path, args.out_path)


if __name__ == "__main__":
    main()
