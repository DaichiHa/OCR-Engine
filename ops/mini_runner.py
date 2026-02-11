import sys, pathlib as _pl
sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))

import os, re, argparse, hashlib, io, contextlib
from PIL import Image
import numpy as np
import cv2
import unicodedata
import pytesseract

# If repository bundles a tesseract binary, prefer it so tests run without system install
_repo_root = _pl.Path(__file__).resolve().parents[1]
# prefer configured tesseract (paths_config.json), else repo-bundled, else system
_bundled_tess = str(_repo_root / "vendor" / "tesseract" / "tesseract.exe")
try:
    from .paths_loader import get_path
    tpath = get_path('tesseract')
except Exception:
    tpath = None
if tpath and os.path.exists(tpath):
    pytesseract.pytesseract.tesseract_cmd = tpath
elif os.path.exists(_bundled_tess):
    pytesseract.pytesseract.tesseract_cmd = _bundled_tess

# ---- knobs (env) ----
INK_MIN   = float(os.getenv("INK_MIN","0.005"))
SOBEL_TH  = float(os.getenv("SOBEL_TH","1.25"))   # gy/gx > th => vertical-ish
# Adjusted table-extraction divisors to reduce over-splitting on this dataset
HK_DIV    = float(os.getenv("HK_DIV","8.0"))      # bigger => shorter kernel
VK_DIV    = float(os.getenv("VK_DIV","6.0"))      # smaller => longer vertical kernel (remove v-lines)
TIMEOUT   = float(os.getenv("TESS_TIMEOUT","8.0"))

def preprocess(pil_img):
    arr=np.array(pil_img)
    if arr.ndim==2: gray=arr
    elif arr.shape[2]==4: gray=cv2.cvtColor(arr, cv2.COLOR_RGBA2GRAY)
    else: gray=cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

    # revert upscale to 2.0 (keep INK_MIN lowered) to isolate effect
    gray=cv2.resize(gray,None,fx=2.0,fy=2.0,interpolation=cv2.INTER_CUBIC)
    gray=cv2.GaussianBlur(gray,(3,3),0)
    th=cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,35,11)
    if th.mean()<127: th=255-th

    inv=255-th
    hh,ww=inv.shape
    hk=cv2.getStructuringElement(cv2.MORPH_RECT,(max(80,int(ww/HK_DIV)),1))
    vk=cv2.getStructuringElement(cv2.MORPH_RECT,(1,max(80,int(hh/VK_DIV))))
    h=cv2.morphologyEx(inv,cv2.MORPH_OPEN,hk,iterations=1)
    v=cv2.morphologyEx(inv,cv2.MORPH_OPEN,vk,iterations=1)
    inv2=cv2.subtract(inv, cv2.bitwise_or(h,v))

    ink=cv2.countNonZero(inv2)/float(inv2.size)
    if ink < INK_MIN:
        return Image.fromarray(np.full(inv2.shape,255,np.uint8))

    inv2=cv2.dilate(inv2,np.ones((2,2),np.uint8),iterations=1)
    out=255-inv2
    out=cv2.copyMakeBorder(out,10,10,10,10,cv2.BORDER_CONSTANT,value=255)
    return Image.fromarray(out)

def sobel_ratio(pil_img):
    arr=np.array(pil_img)
    if arr.ndim==3: arr=cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    gx=cv2.Sobel(arr,cv2.CV_32F,1,0,ksize=3)
    gy=cv2.Sobel(arr,cv2.CV_32F,0,1,ksize=3)
    return float(np.mean(np.abs(gy)))/max(1e-6,float(np.mean(np.abs(gx))))

def scrub(t):
    t=(t or "").strip()
    if re.fullmatch(r"[ \t\r\n\-\—\_\.|:;\"'\`]+", t): return ""
    return t

def digit_score(s):
    if not s: return 0.0
    s=s.replace("，",",").replace("．",".").replace("（","(").replace("）",")")
    d=sum(c.isdigit() for c in s)
    p=sum(c in ".,-()%" for c in s)
    return d*2.0 + p*0.5

def postprocess_text(s):
    if not s:
        return s
    # Unicode normalize to NFKC (convert fullwidth to ascii where appropriate)
    s = unicodedata.normalize('NFKC', s)
    # Replace common punctuation and long dash
    s = s.replace('　', ' ').replace('。', '.').replace('、', ',').replace('ー', '-')
    # Remove control characters
    s = re.sub(r'[\x00-\x1f\x7f]', '', s)

    # If the string contains digits, fix common OCR confusions around numbers
    digits = sum(c.isdigit() for c in s)
    if digits > 0:
        s = re.sub(r'[O〇Ｏ]', '0', s)
        s = re.sub(r'[lI|¡]', '1', s)
        # keep only reasonable characters for mixed numeric fields
        s = re.sub(r"[^0-9A-Za-z\u3040-\u30ff\u3400-\u9fff,().%\- \n]", '', s)
    else:
        # general cleanup: remove odd control punctuation
        s = re.sub(r"[^0-9A-Za-z\u3040-\u30ff\u3400-\u9fff,().%\- \n]", '', s)

    # collapse whitespace
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def patch_tesseract(lang_main):
    orig=pytesseract.image_to_string
    def wrapped(img, **kw):
        if isinstance(img, Image.Image):
            img=preprocess(img)
        cfg=kw.get("config","")
        # Allow overriding PSM/OEM via env vars for sweep testing
        env_psm = os.getenv("TESS_PSM")
        env_oem = os.getenv("TESS_OEM")
        if env_psm:
            # remove existing --psm and set to env value
            cfg = re.sub(r"--psm\s+\d+","", cfg).strip()
            cfg = (cfg + f" --psm {env_psm}").strip()
        else:
            cfg=re.sub(r"--psm\s+\d+","--psm 7",cfg)
            if "--psm" not in cfg: cfg=(cfg+" --psm 7").strip()
        if env_oem:
            cfg = (cfg + f" --oem {env_oem}").strip()
        cfg=(cfg+" -c preserve_interword_spaces=1").strip()

        # Sobel vertical detection => jpn_vert
        use_lang=lang_main
        if isinstance(img, Image.Image):
            r=sobel_ratio(img)
            if r > SOBEL_TH:
                use_lang="jpn_vert+"+lang_main

        kw["config"]=cfg
        kw["lang"]=use_lang
        kw.setdefault("timeout", TIMEOUT)
        t1=scrub(orig(img, **kw))
        t1 = postprocess_text(t1)

        # digits 2-pass (stronger)
        # optionally run a numeric whitelist second pass; disable via env `TESS_DIGIT_2PASS=0`
        if os.getenv("TESS_DIGIT_2PASS","1") == "1":
            kw2=dict(kw)
            kw2["lang"]="eng"
            kw2["config"]=cfg+" -c tessedit_char_whitelist=0123456789.,-()%"

            t2=scrub(orig(img, **kw2))
            t2 = postprocess_text(t2)
            return t2 if digit_score(t2) > digit_score(t1) else t1
        else:
            return t1

    pytesseract.image_to_string=wrapped

def try_slice_rows(mod, r0, r1):
    for name in ["group_cells_into_rows","group_into_rows","cluster_rows"]:
        f=getattr(mod,name,None)
        if callable(f):
            def g(cells,_f=f):
                rows=_f(cells)
                return rows[r0:r1+1]
            setattr(mod,name,g); return True
    return False

def sha256_file(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1024*1024), b""): h.update(b)
    return h.hexdigest()

def jp_rate2(s):
    c=re.sub(r"[\s\|\-—_\.]","",s or "")
    jp=len(re.findall(r"[\u3040-\u30ff\u3400-\u9fff]",c))
    return jp/max(1,len(c))

def noise_rate2(s):
    c=re.sub(r"[\s]","",s or "")
    n=len(re.findall(r"[|\-—_\.]",c))
    return n/max(1,len(c))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--page", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--page-only", action='store_true', help="Run OCR on whole page only (no table extraction)")
    ap.add_argument("--row-min", type=int, default=1)
    ap.add_argument("--row-max", type=int, default=1)
    ap.add_argument("--lang", default="jpn+eng")
    args=ap.parse_args()

    out=_pl.Path(args.out); out.mkdir(parents=True, exist_ok=True)
    patch_tesseract(args.lang)

    # allow skipping table extraction and run full-page OCR for speed comparison
    if args.page_only:
        # do a single-page OCR and produce markdown-like output
        from PIL import Image as PILImage
        im = PILImage.open(args.page)
        txt = pytesseract.image_to_string(im, lang=args.lang, config="")
        txt = postprocess_text(scrub(txt))
        md = "\n" + txt
        buf=io.StringIO()
        buf.write("PAGE-ONLY OCR\n")
        buf.write(str(txt))
    else:
        import ocr_manager as m
        try_slice_rows(m, args.row_min, args.row_max)

        buf=io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            md=m.process_page(args.page, str(out))
        md=md if isinstance(md,str) else ""

    stem=_pl.Path(args.page).stem
    ink=os.getenv("INK_MIN","0.010").replace(".","p")
    out_md=out/f"mini_{stem}_r{args.row_min}-{args.row_max}_ink{ink}.md"
    out_md.write_text(md, encoding="utf-8")

    audit=out/"audit"; audit.mkdir(exist_ok=True)
    (audit/f"{out_md.stem}.runlog.txt").write_text(buf.getvalue(), encoding="utf-8")
    (audit/f"{out_md.stem}.sha256.txt").write_text(
        f"page_sha256={sha256_file(args.page)}\nmd_sha256={sha256_file(out_md)}\n", encoding="utf-8"
    )

    print(str(out_md))
    print("jp_rate2_fix=", round(jp_rate2_fix(md),4), "noise_rate2_fix=", round(noise_rate2_fix(md),4), "INK_MIN=", os.getenv("INK_MIN","0.010"))

# --- PS_KPI_FIX ---
def _clean_for_kpi(s):
    import re
    s = (s or "")
    s = re.sub(r"[\r\n\t ]","", s)
    s = s.replace("|","")
    s = re.sub(r"[—ー_\-\.]","", s)
    return s

def jp_rate2_fix(s):
    import re
    c=_clean_for_kpi(s)
    jp=len(re.findall(r"[\u3040-\u30ff\u3400-\u9fff]", c))
    return jp/max(1,len(c))

def noise_rate2_fix(s):
    import re
    c=_clean_for_kpi(s)
    non=len(re.findall(r"[^0-9A-Za-z\u3040-\u30ff\u3400-\u9fff,()%\-]", c))
    return non/max(1,len(c))
# --- /PS_KPI_FIX ---
if __name__=="__main__":
    main()

