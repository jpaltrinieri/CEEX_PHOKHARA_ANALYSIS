#!/usr/bin/env python3
"""One-line-per-run summary of Phokhara runs: sigma_MC, its 1-photon and 2-photon
parts, and the theta+ / theta- / thav forward-backward asymmetries.

Usage: phok_table.py <run> [<run> ...]      runs under $PHOKHARA_SCRATCH (~/scratch/CEEX_PHOKHARA_ANALYSIS/PHOKHARA)

Per seed: sigma{1,2,}_MC from phokhara.out and the 'Summed lth+/lth-/lthav' blocks
of NLOFF1.dat; merged as the plain mean over seeds, errors sqrt(sum err^2)/N
(same as merge_phokhara.py). A = [s(theta<90) - s(theta>90)] / s. Also prints the
soft cutoff w read from each run's input.dat.
"""
import glob, os, re, sys
import numpy as np

BASE = os.path.expanduser("~/scratch/CEEX_PHOKHARA_ANALYSIS/PHOKHARA")
SIG = re.compile(r"sigma([12]?)_MC\s*\(nbarn\)\s*=\s*(\S+)\s*\+-\s*(\S+)")


def hists(path, names=("lth+", "lth-", "lthav")):
    H, cur = {}, None
    for line in open(path):
        w = line.split()
        if not w or w[0] == "xl":
            continue
        if w[0] == "Summed":
            cur = w[1] if w[1] in names else None
            if cur:
                H[cur] = []
            continue
        if cur:
            try:
                H[cur].append([float(x) for x in w[:4]])
            except ValueError:
                cur = None
    return {k: np.array(v) for k, v in H.items()}


def asym(h):
    w = h[:, 1] - h[:, 0]; s = h[:, 2] * w; e = h[:, 3] * w
    lo, hi = h[:, 1] <= 90, h[:, 0] >= 90
    B, F = s[lo].sum(), s[hi].sum(); eB, eF = np.sqrt((e[lo]**2).sum()), np.sqrt((e[hi]**2).sum())
    T = B + F
    return (B - F) / T, 2 * np.hypot(F * eB, B * eF) / T**2


print(f"{'run':18s} {'w':>7s} {'N':>4s} {'sigma1_MC':>18s} {'sigma2_MC':>18s} {'sigma_MC':>18s}"
      f" {'A(th+)':>17s} {'A(th-)':>17s} {'A(thav)':>17s}")
for run in sys.argv[1:]:
    seeds = [d for d in glob.glob(f"{BASE}/{run}/seed_*")
             if os.path.exists(d + "/done.txt") and os.path.getsize(d + "/NLOFF1.dat") > 0]
    if not seeds:
        print(f"{run:18s}  no finished seeds"); continue
    w = open(seeds[0] + "/input.dat").read().splitlines()[9].split()[0]
    sig = {k: [] for k in ("1", "2", "")}
    H = {k: [] for k in ("lth+", "lth-", "lthav")}
    for d in seeds:
        for m in SIG.finditer(open(d + "/phokhara.out", errors="replace").read()):
            sig[m.group(1)].append((float(m.group(2)), float(m.group(3))))
        h = hists(d + "/NLOFF1.dat")
        for k in H:
            H[k].append(h[k])
    N = len(seeds)
    def msig(k):
        a = np.array(sig[k][-N:]); return a[:, 0].mean(), np.sqrt((a[:, 1]**2).sum()) / N
    def mh(k):
        a = np.stack(H[k]); out = a[0].copy()
        out[:, 2] = a[:, :, 2].mean(0); out[:, 3] = np.sqrt((a[:, :, 3]**2).sum(0)) / N
        return out
    cols = [f"{v:.6f}({e*1e6:.0f})" for v, e in (msig("1"), msig("2"), msig(""))]
    As = [f"{a:+.5f}({e*1e5:.0f})" for a, e in (asym(mh(k)) for k in ("lth+", "lth-", "lthav"))]
    print(f"{run:18s} {w:>7s} {N:4d} " + " ".join(f"{c:>18s}" for c in cols) + " " + " ".join(f"{a:>17s}" for a in As))
