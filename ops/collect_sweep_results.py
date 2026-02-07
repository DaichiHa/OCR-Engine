import os
merge_factors = ['0.5','0.6','0.8']
row_factors = ['0.5','0.8']
h_gaps = ['10','20']

results = []
for mf in merge_factors:
    for rf in row_factors:
        for hg in h_gaps:
            outdir = f"test_sweep_m{mf}_r{rf}_g{hg}_oem3"
            outpath = os.path.join(outdir, 'out.txt')
            kpi = None
            if os.path.exists(outpath):
                with open(outpath, 'r', encoding='utf-8') as f:
                    for line in f:
                        if 'jp_rate2_fix' in line:
                            kpi = line.strip()
                            break
            results.append((mf, rf, hg, kpi))

for mf, rf, hg, kpi in results:
    print(f"mf={mf} rf={rf} hg={hg} -> {kpi}")
