#!/usr/bin/env python3
"""T3: compare CEEX and PHOKHARA per photon multiplicity at a matched soft cutoff.

Usage: t3_compare.py <run> [ecut]      (default ecut 5)

  CEEX     $CEEX_SCRATCH/<run>/RUN_CEEX_*_<ecut>/output_<rank>.txt, histograms <obs>_nph1 /
           <obs>_nph2 (MC_nphsplit with CEEX_NPH_HISTOS=1). Mean over rank files, errors
           sqrt(sum e^2)/N, like merge.py. Rank files flagged by check_total.sh should be
           quarantined first.
  PHOKHARA $PHOKHARA_SCRATCH/<run>/seed_*/NLOFF1.dat with print_summed=1: per observable a
           1-photon block then a 2-photon block, each already dsigma/dx of that channel.

1-photon = Born + virtual + soft (E_gamma < cutoff), 2-photon = hard second photon above the
cutoff; each is cutoff dependent, the sum is not, and for the SAME cutoff both codes must agree
piece by piece. Prints sigma, A(th+), A(th-), A(thav) per piece and the shape chi2/ndf of the
angles and of lmxx on a 60-bin grid.
"""
import glob, os, sys
import numpy as np

run = sys.argv[1]; ecut = sys.argv[2] if len(sys.argv) > 2 else "5"
SC = os.path.expanduser("~/scratch/CEEX_PHOKHARA_ANALYSIS")
OBS = ["lth+", "lth-", "lthav", "lmxx", "lthg", "leg"]
PH_NAME = {"lmxx": "lmmx"}


def ceex_file(p):
    H, cur = {}, None
    for line in open(p):
        if "Histogram:" in line:
            cur = line.split("Histogram:")[1].strip(); H[cur] = []; continue
        if cur is None or not line.split() or line.strip().startswith("Integral"):
            continue
        try:
            H[cur].append([float(x) for x in line.split()[:4]])
        except ValueError:
            cur = None
    return {k: np.array(v) for k, v in H.items() if v}


def phok_file(p):
    """print_summed=1: blocks '<title>' / 'xl xh dxs ddxs' / rows, 1ph then 2ph per obs."""
    blocks, cur = [], None
    for line in open(p):
        w = line.split()
        if not w or w[0].startswith("---") or w[0] in ("MC", "Unweighted"):
            continue
        if w[0] == "xl":
            continue
        try:
            row = [float(x) for x in w[:4]]
            if cur is not None:
                cur[1].append(row)
        except ValueError:
            cur = [w[0].strip('"'), []]; blocks.append(cur)
    out = {}
    names = [b[0] for b in blocks]
    for name in dict.fromkeys(names):
        idx = [i for i, n in enumerate(names) if n == name]
        if len(idx) == 2:
            out[name + "_nph1"] = np.array(blocks[idx[0]][1]); out[name + "_nph2"] = np.array(blocks[idx[1]][1])
    return out


def mean(hs):
    a = np.stack(hs); o = a[0].copy()
    o[:, 2] = a[:, :, 2].mean(0); o[:, 3] = np.sqrt((a[:, :, 3] ** 2).sum(0)) / len(hs)
    return o


def sig(h):
    w = h[:, 1] - h[:, 0]; return (h[:, 2] * w).sum(), np.sqrt(((h[:, 3] * w) ** 2).sum())


def asym(h):
    w = h[:, 1] - h[:, 0]; s = h[:, 2] * w; e = h[:, 3] * w
    lo, hi = h[:, 1] <= 90, h[:, 0] >= 90
    B, F = s[lo].sum(), s[hi].sum(); T = B + F
    return (B - F) / T, 2 * np.hypot(F * np.sqrt((e[lo] ** 2).sum()), B * np.sqrt((e[hi] ** 2).sum())) / T ** 2


def shape_chi2(a, b, k=10):
    n = len(a) // k * k; w = (a[:, 1] - a[:, 0])[:n]
    A = (a[:n, 2] * w).reshape(-1, k).sum(1); B = (b[:n, 2] * w).reshape(-1, k).sum(1)
    eA = np.sqrt(((a[:n, 3] * w) ** 2).reshape(-1, k).sum(1)); eB = np.sqrt(((b[:n, 3] * w) ** 2).reshape(-1, k).sum(1))
    sA, sB = A.sum(), B.sum(); m = (A > 0) & (B > 0)
    r = (A / sA - B / sB)[m]; e = np.hypot(eA / sA, eB / sB)[m]
    return (r ** 2 / e ** 2).sum() / m.sum(), m.sum()


cf = sorted(glob.glob(f"{SC}/CEEX/{run}/RUN_CEEX_*_{ecut}/output_*.txt"))
pf = sorted(glob.glob(f"{SC}/PHOKHARA/{run}/seed_*/NLOFF1.dat"))
pf = [f for f in pf if os.path.exists(os.path.join(os.path.dirname(f), "done.txt")) and os.path.getsize(f) > 0]
C = [ceex_file(f) for f in cf]; C = [h for h in C if "lth+_nph1" in h]
P = [phok_file(f) for f in pf]
print(f"CEEX {len(C)} rank files (ecut {ecut}), PHOKHARA {len(P)} seeds, run {run}\n")
for piece in ("nph1", "nph2", "sum"):
    print(f"== {piece} " + {"nph1": "(Born + virtual + soft)", "nph2": "(hard 2-photon)", "sum": "(total)"}[piece])
    row = {}
    for code, D, nm in (("CEEX", C, lambda o: o), ("PHOKHARA", P, lambda o: PH_NAME.get(o, o))):
        hs = {}
        for o in OBS:
            if piece == "sum":
                h1 = mean([d[nm(o) + "_nph1"] for d in D]); h2 = mean([d[nm(o) + "_nph2"] for d in D])
                h = h1.copy(); h[:, 2] = h1[:, 2] + h2[:, 2]; h[:, 3] = np.hypot(h1[:, 3], h2[:, 3])
            else:
                h = mean([d[nm(o) + "_" + piece] for d in D])
            hs[o] = h
        row[code] = hs
        s, es = sig(hs["lth+"])
        a = [asym(hs[o]) for o in ("lth+", "lth-", "lthav")]
        print(f"  {code:9s} sigma = {s:.6f} +- {es:.6f} nb   A(th+) = {a[0][0]:+.4f}({a[0][1]*1e4:.0f})"
              f"  A(th-) = {a[1][0]:+.4f}({a[1][1]*1e4:.0f})  A(thav) = {a[2][0]:+.4f}({a[2][1]*1e4:.0f})")
    print("  shape chi2/ndf CEEX vs PHOKHARA (60 bins): " + "  ".join(
        f"{o} {shape_chi2(row['CEEX'][o], row['PHOKHARA'][o])[0]:.2f}" for o in OBS))
    print()
