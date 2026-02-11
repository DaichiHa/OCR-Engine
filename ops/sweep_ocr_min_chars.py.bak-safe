import os
import subprocess

py = os.path.join(".", ".venv", "Scripts", "python.exe")
if not os.path.exists(py):
    py = "python"

pages = [
    "page_001.png",
    "page_005.png",
    "page_010.png",
    "page_050.png",
    "page_100.png",
    "page_150.png",
    "page_200.png",
]
min_chars_list = [0, 1, 2, 3, 5]

results = []
for minc in min_chars_list:
    for p in pages:
        img = os.path.join("C:\\Users\\User\\Downloads\\PDF\\_img", p)
        name = os.path.splitext(p)[0]
        outdir = f"test_tblocrmin_min{minc}_{name}"
        if os.path.exists(outdir):
            import shutil

            shutil.rmtree(outdir)
        os.makedirs(outdir, exist_ok=True)
        env = os.environ.copy()
        env["TBL_OCR_MERGE"] = "1"
        env["TBL_OCR_MIN_CHARS"] = str(minc)
        env["TBL_MERGE_FACTOR"] = env.get("TBL_MERGE_FACTOR", "0.8")
        env["MINI_RUNNER_VERBOSE"] = "0"
        env["TESS_TIMEOUT"] = "180"
        env["TESS_PSM"] = "6"
        env["TESS_OEM"] = "3"
        cmd = [
            py,
            "ops\mini_runner.py",
            "--page",
            img,
            "--out",
            outdir,
            "--lang",
            "jpn",
        ]
        try:
            proc = subprocess.run(
                cmd,
                env=env,
                stdout=open(os.path.join(outdir, "out.txt"), "w", encoding="utf-8"),
                stderr=open(os.path.join(outdir, "err.txt"), "w", encoding="utf-8"),
                timeout=90,
            )
        except subprocess.TimeoutExpired:
            print(f"TIMEOUT min={minc} page={p}")
            results.append((minc, p, None))
            continue
        # parse out.txt
        kpi = None
        outpath = os.path.join(outdir, "out.txt")
        if os.path.exists(outpath):
            with open(outpath, "r", encoding="utf-8") as f:
                for line in f:
                    if "jp_rate2_fix" in line:
                        kpi = line.strip()
                        break
        results.append((minc, p, kpi))
        print(f"min={minc} page={p} -> {kpi}")

print("\nSUMMARY:")
for r in results:
    print(r)
