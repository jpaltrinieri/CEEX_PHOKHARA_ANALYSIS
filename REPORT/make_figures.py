#!/usr/bin/env python3
"""Figures for report.tex that are not produced by PLOTS/ (plot_compare.py).

  fig_wscan.pdf   T1/T2/fix: A(theta+) vs soft cutoff w for every PHOKHARA variant
  fig_t3.pdf      T3: dsigma/dtheta+ of the 1-photon and 2-photon parts, CEEX vs PHOKHARA
  fig_t4.pdf      T4: per-point C-odd difference vs the tree interference, and residuals
                      after subtracting H1, H2, H1+H2

Run with the plots env:  ~/.conda/envs/plots/bin/python3 REPORT/make_figures.py
Colours: categorical slots of the dataviz reference palette, in fixed order, one entity
per colour across all figures (CEEX blue, PHOKHARA unpatched orange, fixed aqua, ...).
"""
import glob, os, re, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "figures"); os.makedirs(OUT, exist_ok=True)
SC = os.path.expanduser("~/scratch/CEEX_PHOKHARA_ANALYSIS")
sys.path.insert(0, os.path.join(ROOT, "RUN", "POST_PROCESS"))

# dataviz reference palette, light mode, fixed slot order
S1, S2, S3, S4, S5 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({
    "font.family": "serif", "font.size": 9, "axes.labelsize": 9, "legend.fontsize": 8,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "axes.edgecolor": INK2, "axes.labelcolor": INK,
    "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.axisbelow": True, "lines.linewidth": 1.6,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.03,
})


# ---------------------------------------------------------------- helpers
def phok_seeds(run):
    return [d for d in glob.glob(f"{SC}/PHOKHARA/{run}/seed_*")
            if os.path.exists(d + "/done.txt") and os.path.getsize(d + "/NLOFF1.dat") > 0]


def phok_hist(path, name):
    out, cur = [], False
    for line in open(path):
        w = line.split()
        if not w or w[0] == "xl":
            continue
        if w[0] == "Summed":
            if cur: break
            cur = (w[1] == name); continue
        if cur:
            try: out.append([float(x) for x in w[:4]])
            except ValueError: break
    return np.array(out)


def asym(h):
    w = h[:, 1] - h[:, 0]; s = h[:, 2] * w; e = h[:, 3] * w
    lo, hi = h[:, 1] <= 90, h[:, 0] >= 90
    B, F = s[lo].sum(), s[hi].sum(); T = B + F
    return (B - F) / T, 2 * np.hypot(F * np.sqrt((e[lo]**2).sum()), B * np.sqrt((e[hi]**2).sum())) / T**2


def run_A(run):
    seeds = phok_seeds(run)
    if not seeds:
        return None
    hs = np.stack([phok_hist(d + "/NLOFF1.dat", "lth+") for d in seeds])
    h = hs[0].copy(); h[:, 2] = hs[:, :, 2].mean(0); h[:, 3] = np.sqrt((hs[:, :, 3]**2).sum(0)) / len(seeds)
    return asym(h) + (len(seeds),)


# ---------------------------------------------------------------- fig_wscan
def fig_wscan():
    CEEX, eC = 0.23751, 0.00013
    BB = 0.23724
    variants = [  # (runs by w, label, colour, marker)
        ({-3: "t1_w1e-3", -4: "t1_w1e-4", -5: "t1_w1e-5", -6: "t1_w1e-6"}, "unpatched", S2, "o"),
        ({-4: "t2_h1_w1e-4", -5: "t2_h1_w1e-5", -6: "t2_h1_w1e-6"}, "H1 fixed", S4, "s"),
        ({-4: "t2_h2_w1e-4", -5: "t2_h2_w1e-5", -6: "t2_h2_w1e-6"}, "B5 soft log removed (probe)", S5, "D"),
        ({-4: "t2_h1h2_w1e-4", -5: "t2_h1h2_w1e-5", -6: "t2_h1h2_w1e-6"}, "H1 fixed + B5 soft log removed", S1, "^"),
        ({-3: "t4_fix_w1e-3", -4: "t4_fix_w1e-4", -5: "t4_fix_w1e-5", -6: "t4_fix_w1e-6"}, "fixed: H1 + H3 (30 x 100k)", S3, "v"),
    ]
    hi = {-4: "fix500k_w1e-4", -5: "fix500k_w1e-5", -6: "fix500k_w1e-6"}
    fig, (ax, zx) = plt.subplots(1, 2, figsize=(6.4, 3.3), gridspec_kw={"width_ratios": [1.25, 1]})
    for a in (ax, zx):
        a.axhspan(CEEX - 3 * eC, CEEX + 3 * eC, color=GRID, lw=0, zorder=0)
        a.axhline(CEEX, color=INK2, lw=1.0, zorder=1, label="CEEX-main, prod500k (band: $\\pm3\\sigma$)")
        a.axhline(BB, color=INK2, lw=1.0, ls=(0, (4, 3)), zorder=1, label="BabaYaga")
        a.set_xlabel(r"$\log_{10} w$")
        a.set_xlim(-2.7, -6.3)
    for runs, lab, col, mk in variants:
        pts = [(w, *run_A(r)[:2]) for w, r in sorted(runs.items()) if run_A(r)]
        x, y, e = map(np.array, zip(*pts))
        kw = dict(color=col, marker=mk, ms=5, capsize=0, lw=1.6, zorder=3, markeredgecolor="white", markeredgewidth=0.8)
        ax.errorbar(x, y, yerr=e, label=lab, **kw)
        if "fixed:" in lab:
            zx.errorbar(x, y, yerr=e, **kw)
    pts = [(w, *run_A(r)[:3]) for w, r in sorted(hi.items()) if run_A(r)]
    if pts:
        x, y, e, n = map(np.array, zip(*pts))
        full = int(n.min()) == 300
        lab = "fixed: 300 x 500k" + ("" if full else f" (partial: {int(n.min())}-{int(n.max())} seeds)")
        zx.errorbar(x, y, yerr=e, color=S3, marker="*", ms=10, lw=0, elinewidth=1.6, zorder=4,
                    markeredgecolor=INK, markeredgewidth=0.5, label=lab)
        ax.errorbar([], [], yerr=[], color=S3, marker="*", ms=10, lw=0, markeredgecolor=INK,
                    markeredgewidth=0.5, label=lab)
    ax.set_ylabel(r"$A(\theta^+)$")
    ax.set_title("(a) all variants", fontsize=8.5, color=INK, loc="left")
    zx.set_title("(b) fixed PHOKHARA, zoom", fontsize=8.5, color=INK, loc="left")
    zx.set_ylim(0.2305, 0.2445)
    h, l = ax.get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.22, 1, 1))
    fig.savefig(os.path.join(OUT, "fig_wscan.pdf")); plt.close(fig)


# ---------------------------------------------------------------- fig_t3
def t3_data():
    run, ecut = "t3_split", "5"
    def ceex_file(p):
        H, cur = {}, None
        for line in open(p):
            if "Histogram:" in line:
                cur = line.split("Histogram:")[1].strip(); H[cur] = []; continue
            if cur is None or not line.split() or line.strip().startswith("Integral"):
                continue
            try: H[cur].append([float(x) for x in line.split()[:4]])
            except ValueError: cur = None
        return {k: np.array(v) for k, v in H.items() if v}
    def phok_file(p):
        blocks, cur = [], None
        for line in open(p):
            w = line.split()
            if not w or w[0].startswith("---") or w[0] in ("MC", "Unweighted", "xl"):
                continue
            try:
                row = [float(x) for x in w[:4]]
                if cur is not None: cur[1].append(row)
            except ValueError:
                cur = [w[0], []]; blocks.append(cur)
        idx = [i for i, b in enumerate(blocks) if b[0] == "lth+"]
        return np.array(blocks[idx[0]][1]), np.array(blocks[idx[1]][1])
    def mean(hs):
        a = np.stack(hs); o = a[0].copy(); o[:, 2] = a[:, :, 2].mean(0); o[:, 3] = np.sqrt((a[:, :, 3]**2).sum(0)) / len(hs); return o
    C = [ceex_file(f) for f in sorted(glob.glob(f"{SC}/CEEX/{run}/RUN_CEEX_*_{ecut}/output_*.txt"))]
    C = [c for c in C if "lth+_nph1" in c]
    P = [phok_file(f) for f in sorted(glob.glob(f"{SC}/PHOKHARA/{run}/seed_*/NLOFF1.dat"))]
    return (mean([c["lth+_nph1"] for c in C]), mean([c["lth+_nph2"] for c in C]),
            mean([p[0] for p in P]), mean([p[1] for p in P]))


def rebin(h, k=10):
    n = len(h) // k * k; w = (h[:, 1] - h[:, 0])[:n]
    s = (h[:n, 2] * w).reshape(-1, k).sum(1); e = np.sqrt(((h[:n, 3] * w)**2).reshape(-1, k).sum(1))
    lo = h[:n:k, 0]; hi = h[k - 1:n:k, 1]; W = hi - lo
    return lo, hi, s / W, e / W


def fig_t3_real():
    c1, c2, p1, p2 = t3_data()
    fig, axes = plt.subplots(2, 2, figsize=(6.3, 4.2), sharex=True, gridspec_kw={"height_ratios": [2.2, 1]})
    for j, (c, p, title) in enumerate(((c1, p1, r"1 photon: Born + virtual + soft ($E_\gamma<10^{-5}$ GeV)"),
                                       (c2, p2, r"2 photons: hard emission"))):
        ax, rx = axes[0, j], axes[1, j]
        for h, col, lab in ((c, S1, "CEEX-main"), (p, S2, "PHOKHARA (unpatched)")):
            lo, hi, y, e = rebin(h)
            x = np.r_[lo, hi[-1]]; ax.stairs(y * 1e3, x, color=col, lw=1.6, label=lab)
        ax.set_title(title + "\n" + f"A(θ+): CEEX {asym(c)[0]:.3f},  PHOKHARA {asym(p)[0]:.3f}", fontsize=8.5, color=INK)
        ax.set_ylabel(r"$d\sigma/d\theta^+$ [pb/deg]" if j == 0 else "")
        loc, hic, yc, ec = rebin(c); _, _, yp, ep = rebin(p)
        r = yp / yc; er = r * np.hypot(ep / yp, ec / yc); xc = (loc + hic) / 2
        rx.axhline(1, color=INK2, lw=0.8)
        rx.errorbar(xc, r, yerr=er, color=S2, marker="o", ms=3.5, lw=0, elinewidth=1.2,
                    markeredgecolor="white", markeredgewidth=0.5)
        rx.set_ylabel("PHOKHARA / CEEX" if j == 0 else ""); rx.set_xlabel(r"$\theta^+$ [deg]")
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.04))
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(os.path.join(OUT, "fig_t3.pdf")); plt.close(fig)


# ---------------------------------------------------------------- fig_t4
def fig_t4():
    d = os.path.join(ROOT, "RESULTS", "t4_points")
    P = np.loadtxt(f"{d}/t4_points.txt"); C = np.loadtxt(f"{d}/t4_ceex.txt"); t = P[:, 26:46]; fac = t[:, 12]
    ev = lambda x: (x[0::2] + x[1::2]) / 2; od = lambda x: (x[0::2] - x[1::2]) / 2
    treeP = fac * t[:, 5]; tP = ev(treeP); tC = ev(C[:, 1])
    B3, B4 = fac * t[:, 2], fac * t[:, 3]; verf, vers = t[:, 18], t[:, 19]
    alpha = 1 / 137.035999084; me = 0.51099895e-3; s = 1.02**2; w = 9.8039215686e-6; L = np.log(me**2 / s)
    soft = alpha / np.pi * (-np.log(4 * w * w) * (1 + L) - L**2 / 2 - L - np.pi**2 / 3)
    D = od(P[:, 22:26].sum(1) - treeP) / tP - od(C[:, 6] - C[:, 1]) / tC
    h1 = od(B4 - B3 / 2 * (verf + vers)) / tP; h2 = od(B3 / 2 * (1 + soft)) / tP
    x3 = od(B3) / tP
    fig, (a, b) = plt.subplots(1, 2, figsize=(6.3, 2.9))
    a.plot(x3, D, "o", ms=2.5, color=S2, alpha=0.8, markeredgewidth=0, label="per-point difference D")
    a.plot(x3, h1 + h2, ".", ms=1.2, color=INK, label="prediction H1 + H2")
    a.set_xlabel(r"tree interference $B_3^{\rm odd}/|M_0|^2_{\rm even}$")
    a.set_ylabel(r"$D$ = PHOKHARA $-$ CEEX  (C-odd, /tree)")
    a.legend(loc="upper left", markerscale=2)
    bins = np.linspace(-8, 0, 49)
    for r, col, lab in ((D, S2, "none"), (D - h2, S5, "H2 only"), (D - h1, S4, "H1 only"), (D - h1 - h2, S3, "H1 + H2")):
        b.hist(np.log10(np.abs(r) + 1e-12), bins=bins, histtype="step", color=col, lw=1.6,
               label=f"{lab}: rms {r.std():.1e}")
    b.set_xlabel(r"$\log_{10}|D - {\rm subtracted}|$"); b.set_ylabel("points")
    b.legend(title="subtracted", title_fontsize=8, loc="upper left")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_t4.pdf")); plt.close(fig)


if __name__ == "__main__":
    which = sys.argv[1:] or ["wscan", "t3", "t4"]
    if "wscan" in which: fig_wscan()
    if "t3" in which: fig_t3_real()
    if "t4" in which: fig_t4()
    print("figures ->", OUT, sorted(os.listdir(OUT)))
