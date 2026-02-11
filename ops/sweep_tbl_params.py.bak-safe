import os
import subprocess
from itertools import product

py = os.path.join(".", ".venv", "Scripts", "python.exe")
if not os.path.exists(py):
    py = "python"

merge_factors = ["0.5", "0.6", "0.8"]
row_factors = ["0.5", "0.8"]
h_gaps = ["10", "20"]

for mf, rf, hg in product(merge_factors, row_factors, h_gaps):
    outdir = f"test_sweep_m{mf}_r{rf}_g{hg}_oem3"
    if os.path.exists(outdir):
        import shutil

        shutil.rmtree(outdir)
    os.makedirs(outdir, exist_ok=True)
    env = os.environ.copy()
    env["TBL_MERGE_FACTOR"] = mf
    env["TBL_ROW_TOL_FACTOR"] = rf
    env["TBL_H_GAP"] = hg
    env["MINI_RUNNER_VERBOSE"] = "1"
    env["TESS_TIMEOUT"] = "180"
    env["TESS_PSM"] = "6"
    env["TESS_OEM"] = "3"

    print(f"--- RUN mf={mf} rf={rf} hg={hg} -> {outdir} ---")
    cmd = [
        py,
        os.path.join("ops", "mini_runner.py"),
        "--page",
        r"C:\Users\User\Downloads\PDF\_img\page_001.png",
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
        print("TIMEOUT")
        continue
    except Exception as e:
        print("ERROR", e)
        continue

    # read first lines of out.txt
    out_path = os.path.join(outdir, "out.txt")
    if os.path.exists(out_path):
        with open(out_path, "r", encoding="utf-8") as f:
            for _ in range(20):
                line = f.readline()
                if not line:
                    break
                print(line.rstrip())
    else:
        print("NO out.txt")

print("SWEEP DONE")
