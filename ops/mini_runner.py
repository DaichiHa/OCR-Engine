import sys, pathlib as _pl
sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))  # repo root

import os, re, argparse, hashlib, io, contextlib
from PIL import Image
import numpy as np
import cv2
import pytesseract

def preprocess(pil_img):
    arr = np.array(pil_img)
    if arr.ndim == 2:
        gray = arr
    elif arr.shape[2] == 4:
        gray = cv2.cvtColor(arr, cv2.COLOR_RGBA2GRAY)
    else:
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

    gray = cv2.resize(gray, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
    gray = cv2.GaussianBlur(gray, (3,3), 0)
    th = cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,35,11)
    if th.mean() < 127: th = 255 - th

    inv = 255 - th
    hh, ww = inv.shape
    hk = cv2.getStructuringElement(cv2.MORPH_RECT, (max(80, ww//6), 1))
    vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(80, hh//6)))
    h = cv2.morphologyEx(inv, cv2.MORPH_OPEN, hk, iterations=1)
    v = cv2.morphologyEx(inv, cv2.MORPH_OPEN, vk, iterations=1)
    inv2 = cv2.subtract(inv, cv2.bitwise_or(h, v))

    ink = cv2.countNonZero(inv2) / float(inv2.size)
    if ink < float(os.getenv("INK_MIN","0.010")):
        return Image.fromarray(np.full(inv2.shape,255,np.uint8))

    inv2 = cv2.dilate(inv2, np.ones((2,2),np.uint8), iterations=1)
    out = 255 - inv2
    out = cv2.copyMakeBorder(out,10,10,10,10,cv2.BORDER_CONSTANT,value=255)
    return Image.fromarray(out)

def scrub(t):
    t = (t or "").strip()
    if re.fullmatch(r"[ \t\r\n\-\—\_\.|:;\"'\`]+", t): return ""
    return t

def jp_rate(s):
    jp = len(re.findall(r"[\u3040-\u30ff\u3400-\u9fff]", s))
    return jp / max(1, len(s))

def noise_rate(s):
    n = len(re.findall(r"[|\-\—_\.]", s))
    return n / max(1, len(s))

def patch_tesseract(timeout_s, lang_main, digit_pass=True, vert_pass=True):
    orig = pytesseract.image_to_string
    def wrapped(img, **kw):
        if isinstance(img, Image.Image):
            img = preprocess(img)
        cfg = kw.get("config","")
        cfg = re.sub(r"--psm\s+\d+","--psm 7", cfg)
        if "--psm" not in cfg: cfg = (cfg + " --psm 7").strip()
        cfg = (cfg + " -c preserve_interword_spaces=1").strip()

        use_lang = lang_main
        if vert_pass and isinstance(img, Image.Image):
            w,h = img.size
            if h > 2.2*w: use_lang = "jpn_vert+" + lang_main

        kw["config"]=cfg
        kw.setdefault("timeout", timeout_s)
        kw["lang"]=use_lang
        t1 = scrub(orig(img, **kw))

        if not digit_pass:
            return t1

        kw2 = dict(kw)
        kw2["lang"]="eng"
        kw2["config"]=cfg + " -c tessedit_char_whitelist=0123456789.,-"
        t2 = scrub(orig(img, **kw2))

        d1 = sum(c.isdigit() for c in t1) / max(1, len(t1))
        d2 = sum(c.isdigit() for c in t2) / max(1, len(t2))
        if len(t2) >= 2 and d2 > d1: return t2
        return t1

    pytesseract.image_to_string = wrapped

def try_slice_rows(mod, r0, r1):
    for name in ["group_cells_into_rows","group_into_rows","cluster_rows"]:
        f = getattr(mod, name, None)
        if callable(f):
            def g(cells, _f=f):
                rows = _f(cells)
                return rows[r0:r1+1]
            setattr(mod, name, g)
            return True
    return False

def sha256_file(p):
    h = hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1024*1024), b""):
            h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--page", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--row-min", type=int, default=1)
    ap.add_argument("--row-max", type=int, default=1)
    ap.add_argument("--timeout", type=float, default=0.8)
    ap.add_argument("--lang", default="jpn+eng")
    args=ap.parse_args()

    out=_pl.Path(args.out); out.mkdir(parents=True, exist_ok=True)
    patch_tesseract(args.timeout, args.lang, digit_pass=True, vert_pass=True)

    import ocr_manager as m
    try_slice_rows(m, args.row_min, args.row_max)

    buf=io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        md = m.process_page(args.page, str(out))
    md = md if isinstance(md, str) else ""

    stem=_pl.Path(args.page).stem
    ink=os.getenv("INK_MIN","na").replace(".","p")
    out_md = out / f"mini_{stem}_r{args.row_min}-{args.row_max}_ink{ink}.md"
    out_md.write_text(md, encoding="utf-8")

    audit = out / "audit"
    audit.mkdir(exist_ok=True)
    (audit / f"{out_md.stem}.runlog.txt").write_text(buf.getvalue(), encoding="utf-8")
    (audit / f"{out_md.stem}.sha256.txt").write_text(
        f"page_sha256={sha256_file(args.page)}\nmd_sha256={sha256_file(out_md)}\n",
        encoding="utf-8"
    )

    print(str(out_md))
    print("jp_rate=", round(jp_rate(md),4), "noise_rate=", round(noise_rate(md),4), "ink_min=", os.getenv("INK_MIN","na"))

if __name__=="__main__":
    main()
