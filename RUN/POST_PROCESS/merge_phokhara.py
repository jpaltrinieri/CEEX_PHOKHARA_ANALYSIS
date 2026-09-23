#!/usr/bin/env python3
"""
Merge a Phokhara production (one seed_<k>/ per SLURM array task, see
RUN/RUN_PHOKHARA/submit.sh) into per-observable CSVs in the same
format as the old reference set:

    <out_dir>/NLOFF1_<obs>.csv      xl,xh,NLOFF1,dNLOFF1
    <out_dir>/sigma.txt             total cross sections, per-seed and merged
    <out_dir>/seeds.txt             which seeds went in (and which were skipped)

Input, per seed:
    NLOFF1.dat     written by endhistoMC() with print_summed=0: a
                   "MC histograms" section of "Summed <title>" blocks, each
                   "xl xh dxs ddxs" rows -- already dsigma/dx in nb/unit,
                   normalised by that seed's own event count.
    phokhara.out   "sigma (nbarn) = s +- ds" and "sigma_MC (nbarn) s +- ds" (no "=").
    done.txt       "exit=<rc> ...": a seed is merged only if rc == 0.

Every seed runs the same number of events, so the merge is the plain mean over
seeds and the error is sqrt(sum err_k^2)/N. The seed-to-seed scatter is
reported next to it in sigma.txt as a check on the per-seed errors.

Usage:
    merge_phokhara.py <phokhara_run_dir> <out_dir>
    e.g. merge_phokhara.py ~/scratch/CEEX_PHOKHARA_ANALYSIS/PHOKHARA/<run> ../../PLOTS/DATA/<run>/phokhara
"""
import glob
import os
import re
import sys

import numpy as np

SIGMA_RE = re.compile(r"sigma(_MC)?\s*\(nbarn\)\s*=?\s*([-+0-9.EeDd]+)\s*\+-\s*([-+0-9.EeDd]+)")


def fnum(s):
    return float(s.replace("D", "E").replace("d", "e"))


def read_histos(path):
    """Return {title: array (nbins, 4)} from the 'MC histograms' section."""
    hists, cur, in_mc = {}, None, False
    with open(path) as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            if s.startswith("MC histograms"):
                in_mc, cur = True, None
                continue
            if s.startswith("Unweighted histograms"):
                in_mc, cur = False, None
                continue
            if not in_mc or s.startswith("---") or s.startswith("xl xh"):
                continue
            if s.startswith("Summed"):
                cur = s[len("Summed"):].strip().strip('"').strip()
                hists[cur] = []
                continue
            if cur is None:
                continue
            try:
                hists[cur].append([fnum(x) for x in s.split()[:4]])
            except ValueError:
                cur = None
    return {k: np.array(v) for k, v in hists.items() if v}


def read_sigma(path):
    out = {}
    if not os.path.exists(path):
        return out
    with open(path) as f:
        for line in f:
            m = SIGMA_RE.search(line)
            if m:
                out["sigma_MC" if m.group(1) else "sigma"] = (fnum(m.group(2)), fnum(m.group(3)))
    return out


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    run_dir, out_dir = sys.argv[1], sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)

    seeds, skipped = [], []
    for d in sorted(glob.glob(os.path.join(run_dir, "seed_*")),
                    key=lambda p: int(p.rsplit("_", 1)[1])):
        done = os.path.join(d, "done.txt")
        dat = os.path.join(d, "NLOFF1.dat")
        if not os.path.exists(done):
            skipped.append((d, "no done.txt (running or killed)"))
            continue
        rc = re.search(r"exit=(\d+)", open(done).read())
        if not rc or rc.group(1) != "0":
            skipped.append((d, f"done.txt: {open(done).read().strip()}"))
            continue
        if not os.path.exists(dat) or os.path.getsize(dat) == 0:
            skipped.append((d, "empty NLOFF1.dat"))
            continue
        h = read_histos(dat)
        if not h:
            skipped.append((d, "no 'Summed' blocks in NLOFF1.dat"))
            continue
        seeds.append((d, h, read_sigma(os.path.join(d, "phokhara.out"))))

    print(f"[merge_phokhara] {len(seeds)} seed(s) merged, {len(skipped)} skipped from {run_dir}")
    for d, why in skipped:
        print(f"    skip {os.path.basename(d)}: {why}")
    if not seeds:
        sys.exit(1)

    names = list(seeds[0][1].keys())
    n = len(seeds)
    for name in names:
        arrs = [h[name] for _, h, _ in seeds if name in h]
        if len(arrs) != n or any(a.shape != arrs[0].shape for a in arrs):
            print(f"    WARNING {name}: missing or mis-shaped in some seeds, skipped")
            continue
        stack = np.stack(arrs)                       # (seed, bin, col)
        val = stack[:, :, 2].mean(0)
        err = np.sqrt((stack[:, :, 3] ** 2).sum(0)) / n
        with open(os.path.join(out_dir, f"NLOFF1_{name}.csv"), "w") as f:
            f.write("xl,xh,NLOFF1,dNLOFF1\n")
            for (xl, xh), v, e in zip(stack[0, :, :2], val, err):
                f.write(f"{float(xl)!r},{float(xh)!r},{float(v)!r},{float(e)!r}\n")

    with open(os.path.join(out_dir, "sigma.txt"), "w") as f:
        f.write(f"# merged from {run_dir}: {n} seeds\n")
        for key in ("sigma", "sigma_MC"):
            per = np.array([s[key] for _, _, s in seeds if key in s])
            if len(per) == 0:
                continue
            mean = per[:, 0].mean()
            err = np.sqrt((per[:, 1] ** 2).sum()) / len(per)
            scatter = per[:, 0].std(ddof=1) / np.sqrt(len(per)) if len(per) > 1 else float("nan")
            f.write(f"{key:9s} = {mean:.6f} +- {err:.6f} nb  "
                    f"(seed-scatter error {scatter:.6f}, {len(per)} seeds)\n")
    with open(os.path.join(out_dir, "seeds.txt"), "w") as f:
        for d, _, _ in seeds:
            f.write(f"merged  {d}\n")
        for d, why in skipped:
            f.write(f"skipped {d}  ({why})\n")
    print(open(os.path.join(out_dir, "sigma.txt")).read(), end="")
    print(f"[merge_phokhara] {len(names)} histogram(s) -> {out_dir}/")


if __name__ == "__main__":
    main()
