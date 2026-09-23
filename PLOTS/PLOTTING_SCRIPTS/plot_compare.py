#!/usr/bin/env python3
"""
CEEX vs Phokhara for KLOE-LA (KLOE-I), e+e- -> pi+pi-gamma, fixed-order NLO,
F(pi) = 1, no vacuum polarisation.

The discrepancy this is built for: the total cross sections agree, but the
pion polar-angle distributions (lth+, lth-, lthav) do not. Every plot carries
two ratio panels under the distribution:
  (1) CEEX / BabaYaga                  CEEX against the independent NLO code it agrees with
  (2) {CEEX, BabaYaga} / Phokhara      both against Phokhara, where the tilt shows
Each numerator carries its own MC error; the denominator's error is the band
around 1, in its colour. The old Phokhara set is drawn in the distribution only.

Sources, all optional, read from the data directory (argv[1]):
  ceex/merged_histograms_<ecut>.txt  CEEX main, one per Emin     (RUN/POST_PROCESS ceex)
  phokhara/NLOFF1_<obs>.csv          Phokhara, new production   (RUN/POST_PROCESS phokhara)
  phokhara_ref/NLOFF1_<obs>.csv      Phokhara, old reference set (CEEX_ANALYSIS, 5 Aug)
  babayaga/BB_<obs>.txt              BabaYaga NLO, F(pi)=1
A missing source is reported and left out, so this runs before every source
exists (e.g. new vs old Phokhara while CEEX is still running).

All sources are put onto one grid per observable -- the first CEEX ecut's 600
uniform bins, else the first source that has the observable -- with an
area-weighted overlap projection (the identity where edges agree, which they
do for Phokhara's 600-bin card). Every plot is made at 600, 60 and 10 bins.

Outputs (argv[2]):
  <nbins>bins/pi_kloe_la_<obs>.pdf       per observable: distribution + ratio panels (1), (2)
  <nbins>bins/overview_vs_babayaga.pdf   panel (1) for every observable on one page
  <nbins>bins/overview_vs_phokhara.pdf   panel (2) for every observable on one page
  summary.txt                        sigma per source, shape chi2/ndf vs the
                                     reference, forward-backward asymmetries,
                                     and the C-mirror test theta+ <-> 180-theta-

Usage:
  plot_compare.py DATA RESULTS [--phokhara=phokhara|phokhara_ref]
                  [--ecuts=4,5] [--no-preview]
--phokhara picks the Phokhara set of panel (2); default: the new run
(phokhara), else the old reference set (phokhara_ref).
"""
import csv
import glob
import os
import re
import sys
from collections import OrderedDict

import matplotlib
matplotlib.use("Agg")
import matplotlib.gridspec as gridspec
import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plot_style import (BG_COLOR, NLO_COLOR, apply_global_style, compute_ratio,
                        compute_ratio_ylimits, format_ecut_label,
                        integrate_xs, make_step, make_step_band, make_step_values,
                        style_axis)
from terminal_preview import preview_pdf

apply_global_style()

# ── arguments ─────────────────────────────────────────────────────────────────
pos = [a for a in sys.argv[1:] if not a.startswith("--")]
opt = {a.split("=", 1)[0]: (a.split("=", 1)[1] if "=" in a else True)
       for a in sys.argv[1:] if a.startswith("--")}
data_dir = pos[0] if len(pos) > 0 else "DATA"
out_dir = pos[1] if len(pos) > 1 else "RESULTS"
ECUTS = set(opt["--ecuts"].split(",")) if "--ecuts" in opt else None
DO_PREVIEW = "--no-preview" not in opt

REBIN_VARIANTS = [(1, "600bins"), (10, "60bins"), (60, "10bins")]

OBS_ORDER = ["lth+", "lth-", "lthav", "lthg", "lp+", "lp-", "lpz+", "lpz-",
             "lpp+", "lpp-", "lmxx", "lxi", "ldphi", "leg",
             "lmxxg", "lmtrk", "lmxxc", "lmtrkc"]
PHOK_NAME = {"lmxx": "lmmx"}          # Phokhara's file name for CEEX's lmxx
ANGLE_OBS = ("lth+", "lth-", "lthav")  # the observables the discrepancy is in

LABELS = {
    "lth+": (r"$\theta^+$ [deg]", r"$\mathrm{d}\sigma/\mathrm{d}\theta^+$"),
    "lth-": (r"$\theta^-$ [deg]", r"$\mathrm{d}\sigma/\mathrm{d}\theta^-$"),
    "lthav": (r"$\theta_\mathrm{av}$ [deg]", r"$\mathrm{d}\sigma/\mathrm{d}\theta_\mathrm{av}$"),
    "lthg": (r"$\theta_\gamma$ [deg]", r"$\mathrm{d}\sigma/\mathrm{d}\theta_\gamma$"),
    "lp+": (r"$p^+$ [MeV]", r"$\mathrm{d}\sigma/\mathrm{d}p^+$"),
    "lp-": (r"$p^-$ [MeV]", r"$\mathrm{d}\sigma/\mathrm{d}p^-$"),
    "lpz+": (r"$|p_z^+|$ [MeV]", r"$\mathrm{d}\sigma/\mathrm{d}p_z^+$"),
    "lpz-": (r"$|p_z^-|$ [MeV]", r"$\mathrm{d}\sigma/\mathrm{d}p_z^-$"),
    "lpp+": (r"$p_\perp^+$ [MeV]", r"$\mathrm{d}\sigma/\mathrm{d}p_\perp^+$"),
    "lpp-": (r"$p_\perp^-$ [MeV]", r"$\mathrm{d}\sigma/\mathrm{d}p_\perp^-$"),
    "lmxx": (r"$m_{\pi\pi}$ [MeV]", r"$\mathrm{d}\sigma/\mathrm{d}m_{\pi\pi}$"),
    "lxi": (r"$\xi$ [deg]", r"$\mathrm{d}\sigma/\mathrm{d}\xi$"),
    "ldphi": (r"$\Delta\phi$ [deg]", r"$\mathrm{d}\sigma/\mathrm{d}\Delta\phi$"),
    "leg": (r"$E_\gamma$ [MeV]", r"$\mathrm{d}\sigma/\mathrm{d}E_\gamma$"),
    "lmxxg": (r"$m_{\pi\pi\gamma}$ [MeV]", r"$\mathrm{d}\sigma/\mathrm{d}m_{\pi\pi\gamma}$"),
    "lmtrk": (r"$m_\mathrm{trk}$ [MeV]", r"$\mathrm{d}\sigma/\mathrm{d}m_\mathrm{trk}$"),
    "lmxxc": (r"$m_{\pi\pi}^\mathrm{c}$ [MeV]", r"$\mathrm{d}\sigma/\mathrm{d}m_{\pi\pi}^\mathrm{c}$"),
    "lmtrkc": (r"$m_\mathrm{trk}^\mathrm{c}$ [MeV]", r"$\mathrm{d}\sigma/\mathrm{d}m_\mathrm{trk}^\mathrm{c}$"),
}

CUTS_TEXT = [
    r"KLOE-LA, $\pi^+\pi^-\gamma$, NLO, $F_\pi=1$, no VP",
    r"$50^\circ \leq \theta_\pm \leq 130^\circ$",
    r"$|p^z_\pm| > 90\,\mathrm{MeV}$ or $p^\perp_\pm > 160\,\mathrm{MeV}$",
    r"$50^\circ \leq \theta_\gamma \leq 130^\circ$, $E_\gamma > 20\,\mathrm{MeV}$",
    r"$0.1 \leq M_{XX}^2 \leq 0.85\,\mathrm{GeV}^2$",
]


# ── readers: every source becomes {obs: [(xl, xh, val, err), ...]} ────────────
def read_ceex(path):
    hists, cur = OrderedDict(), None
    with open(path) as f:
        for line in f:
            s = line.strip()
            if s.startswith("Histogram:"):
                cur = s.split(":", 1)[1].strip()
                hists[cur] = []
            elif cur and s:
                p = s.split()
                if len(p) >= 4:
                    try:
                        hists[cur].append(tuple(map(float, p[:4])))
                    except ValueError:
                        pass
    return {k: v for k, v in hists.items() if v}


def read_phokhara_dir(d):
    out = {}
    for obs in OBS_ORDER:
        f = os.path.join(d, f"NLOFF1_{PHOK_NAME.get(obs, obs)}.csv")
        if not os.path.exists(f):
            continue
        with open(f) as fh:
            rows = list(csv.DictReader(fh))
        if rows:
            out[obs] = [(float(r["xl"]), float(r["xh"]), float(r["NLOFF1"]),
                         float(r["dNLOFF1"])) for r in rows]
    return out


def read_babayaga_dir(d):
    out = {}
    for obs in OBS_ORDER:
        f = os.path.join(d, f"BB_{obs}.txt")
        if not os.path.exists(f):
            continue
        a = np.loadtxt(f, delimiter=",", skiprows=1, ndmin=2)
        if len(a) < 2:
            continue
        w = a[1, 0] - a[0, 0]
        out[obs] = [(x, x + w, v, e) for x, v, e in a]
    return out


# Source registry, in drawing order. style: (color, linestyle, linewidth)
sources = OrderedDict()   # key -> dict(label, hists, style)

ceex_files = sorted(glob.glob(os.path.join(data_dir, "ceex", "merged_histograms_*.txt")),
                    key=lambda p: int(re.search(r"_(\d+)\.txt$", p).group(1)))
ceex_ecuts = [re.search(r"_(\d+)\.txt$", p).group(1) for p in ceex_files]
if ECUTS:
    ceex_files = [p for p, e in zip(ceex_files, ceex_ecuts) if e in ECUTS]
    ceex_ecuts = [e for e in ceex_ecuts if e in ECUTS]
# darker than plot_style's get_ecut_colors(), whose first shade is near white:
# here CEEX has to stay visible on top of BabaYaga, which it overlays exactly
_n = len(ceex_files)
ceex_colors = [matplotlib.colormaps["Greys"](0.95 if _n <= 1 else 0.5 + 0.45 * i / (_n - 1))
               for i in range(_n)]
for (p, e), c in zip(zip(ceex_files, ceex_ecuts), ceex_colors):
    sources[f"ceex{e}"] = dict(label=f"CEEX main ({format_ecut_label(e)})",
                               hists=read_ceex(p), style=(c, "-", 1.3))
for key, sub, label, reader, style in [
        ("phokhara", "phokhara", "Phokhara NLO (new run)", read_phokhara_dir, (NLO_COLOR, "-", 1.5)),
        ("phokhara_ref", "phokhara_ref", "Phokhara NLO (old ref.)", read_phokhara_dir, ("#e6994d", "--", 1.4)),
        ("babayaga", "babayaga", "BabaYaga NLO", read_babayaga_dir, ("#1f4fd1", (0, (5, 2.5)), 1.9))]:
    d = os.path.join(data_dir, sub)
    h = reader(d) if os.path.isdir(d) else {}
    if h:
        sources[key] = dict(label=label, hists=h, style=style)

for key in ["ceex", "phokhara", "phokhara_ref", "babayaga"]:
    found = [k for k in sources if k.startswith(key) and (key != "phokhara" or k == key)]
    print(f"{'✅' if found else '⚠️ '} {key:13s}: "
          + (", ".join(f"{k} ({len(sources[k]['hists'])} obs)" for k in found) if found else "not found"))
if len(sources) < 1:
    sys.exit("no source found under " + data_dir)

# Ratio panels: (1) CEEX / BabaYaga, (2) {CEEX, BabaYaga} / Phokhara.
# REF is the Phokhara set used as denominator of (2), and the reference of the
# shape-chi2 table in summary.txt: the new run, else the old reference set.
REF = opt.get("--phokhara") or ("phokhara" if "phokhara" in sources else
                                "phokhara_ref" if "phokhara_ref" in sources else None)
if REF is None or REF not in sources:
    sys.exit(f"--phokhara={REF}: no Phokhara set available; have {', '.join(sources)}")
BB = "babayaga" if "babayaga" in sources else None
# Numerators over BabaYaga, in panel (1) and the "vs babayaga" table: CEEX when
# there is any, else the Phokhara sets -- so Phokhara / BabaYaga is shown while
# CEEX is still running.
HAVE_CEEX = any(k.startswith("ceex") for k in sources)
PANEL1 = "CEEX / BabaYaga" if HAVE_CEEX else "Phokhara / BabaYaga"


def bb_nums(keys):
    if HAVE_CEEX:
        return [k for k in keys if k.startswith("ceex")]
    return [k for k in dict.fromkeys([REF, "phokhara", "phokhara_ref"]) if k in keys]


if BB is None:
    print(f"⚠️  no BabaYaga: the {PANEL1} panel is dropped")
elif not HAVE_CEEX:
    print("⚠️  no CEEX: panel (1) and the BabaYaga table show Phokhara / BabaYaga")
print(f"Phokhara denominator: {sources[REF]['label']}")


# ── binning ───────────────────────────────────────────────────────────────────
def rebin_onto(src, target):
    """Area-weighted projection of a differential distribution onto target edges."""
    out, j = [], 0
    for tlo, thi, *_ in target:
        w, area, err2 = thi - tlo, 0.0, 0.0
        while j < len(src) and src[j][1] <= tlo:
            j += 1
        k = j
        while k < len(src) and src[k][0] < thi:
            slo, shi, v, e = src[k]
            ov = min(shi, thi) - max(slo, tlo)
            if ov > 0:
                area += v * ov
                err2 += (e * ov) ** 2
            k += 1
        out.append((tlo, thi, area / w if w > 0 else 0.0, err2 ** 0.5 / w if w > 0 else 0.0))
    return out


def group_bins(bins, g):
    if g <= 1:
        return list(bins)
    out = []
    for i in range(0, len(bins) - len(bins) % g, g):
        ch = bins[i:i + g]
        w = ch[-1][1] - ch[0][0]
        a = sum(v * (hi - lo) for lo, hi, v, _ in ch)
        e2 = sum((e * (hi - lo)) ** 2 for lo, hi, _, e in ch)
        out.append((ch[0][0], ch[-1][1], a / w, e2 ** 0.5 / w))
    return out


def base_grid(obs):
    for k, s in sources.items():
        if obs in s["hists"]:
            return s["hists"][obs]
    return None


def common_range(obs, have):
    """Overlap of the x-ranges of every source that has `obs` (BabaYaga's
    theta files, for instance, start at 30 deg, zero padded)."""
    lo = max(sources[k]["hists"][obs][0][0] for k in have)
    hi = min(sources[k]["hists"][obs][-1][1] for k in have)
    return lo, hi


def on_grid(obs, group):
    """{source: bins} for every source having `obs`, all on one grid."""
    have = [k for k in sources if obs in sources[k]["hists"]]
    lo, hi = common_range(obs, have)
    grid = [b for b in base_grid(obs) if b[0] >= lo - 1e-9 and b[1] <= hi + 1e-9]
    grid = group_bins(grid, group)
    return {k: rebin_onto(sources[k]["hists"][obs], grid) for k in have}


def shape(bins):
    s, _ = integrate_xs(bins)
    return [(lo, hi, v / s, e / s) for lo, hi, v, e in bins] if s else bins


# ── statistics for summary.txt ────────────────────────────────────────────────
def chi2_shape(a, b):
    a, b = shape(a), shape(b)
    num, n = 0.0, 0
    for (_, _, va, ea), (_, _, vb, eb) in zip(a, b):
        e2 = ea ** 2 + eb ** 2
        if e2 > 0 and (va != 0 or vb != 0):
            num += (va - vb) ** 2 / e2
            n += 1
    return num / max(n - 1, 1), n


def fb_asym(bins, split=90.0):
    """(sigma(x < split) - sigma(x > split)) / sigma, with its error."""
    f = sum(v * (hi - lo) for lo, hi, v, _ in bins if hi <= split + 1e-9)
    b = sum(v * (hi - lo) for lo, hi, v, _ in bins if lo >= split - 1e-9)
    ef2 = sum((e * (hi - lo)) ** 2 for lo, hi, _, e in bins if hi <= split + 1e-9)
    eb2 = sum((e * (hi - lo)) ** 2 for lo, hi, _, e in bins if lo >= split - 1e-9)
    t = f + b
    if t == 0:
        return float("nan"), float("nan")
    return (f - b) / t, 2 * np.sqrt(b * b * ef2 + f * f * eb2) / t ** 2


def mirror_chi2(thp, thm):
    """C invariance: dsigma/dtheta+(theta) = dsigma/dtheta-(180-theta) exactly.
    Both on the same symmetric grid about 90 deg, so reversing is the mirror."""
    m = list(reversed(thm))
    num, n = 0.0, 0
    for (lo, hi, a, ea), (_, _, b, eb) in zip(thp, m):
        e2 = ea ** 2 + eb ** 2
        if e2 > 0:
            num += (a - b) ** 2 / e2
            n += 1
    return num / max(n, 1), n


def write_summary(path, group=10):
    L = []
    L.append("CEEX vs Phokhara -- KLOE-LA pi+pi-gamma NLO, F(pi)=1, no VP")
    L.append(f"data: {os.path.abspath(data_dir)}")
    L.append(f"reference (ratio denominator): {REF} = {sources[REF]['label']}")
    L.append("")
    L.append("sigma [nb], integral of each observable over the common range")
    obs_all = [o for o in OBS_ORDER if any(o in s["hists"] for s in sources.values())]
    head = f"{'obs':8s}" + "".join(f"{k:>24s}" for k in sources)
    L.append(head)
    for obs in obs_all:
        g = on_grid(obs, 1)
        row = f"{obs:8s}"
        for k in sources:
            if k in g:
                s, e = integrate_xs(g[k])
                row += f"{s:>14.5f} ±{e:8.5f}"
            else:
                row += f"{'-':>24s}"
        L.append(row)
    L.append("")
    L.append(f"shape chi2/ndf vs {REF} ({600 // group}-bin grid; each distribution "
             "normalised to its own sigma)")
    L.append(f"{'obs':8s}" + "".join(f"{k:>16s}" for k in sources if k != REF))
    for obs in obs_all:
        g = on_grid(obs, group)
        if REF not in g:
            continue
        row = f"{obs:8s}"
        for k in sources:
            if k == REF:
                continue
            if k in g:
                c, n = chi2_shape(g[k], g[REF])
                row += f"{c:>11.2f} ({n:2d})"
            else:
                row += f"{'-':>16s}"
        L.append(row + ("   <-- angle" if obs in ANGLE_OBS else ""))
    if BB:
        L.append("")
        L.append(f"shape chi2/ndf vs babayaga ({600 // group}-bin grid)")
        ce = bb_nums(list(sources))
        L.append(f"{'obs':8s}" + "".join(f"{k:>16s}" for k in ce))
        for obs in obs_all:
            g = on_grid(obs, group)
            if BB not in g or not any(k in g for k in ce):
                continue
            row = f"{obs:8s}"
            for k in ce:
                if k in g:
                    c, n = chi2_shape(g[k], g[BB])
                    row += f"{c:>11.2f} ({n:2d})"
                else:
                    row += f"{'-':>16s}"
            L.append(row + ("   <-- angle" if obs in ANGLE_OBS else ""))
    L.append("")
    L.append("forward-backward asymmetry A = [sigma(<90) - sigma(>90)] / sigma")
    L.append(f"{'obs':8s}" + "".join(f"{k:>22s}" for k in sources))
    for obs in ("lth+", "lth-", "lthav", "lthg"):
        g = on_grid(obs, 1) if any(obs in s["hists"] for s in sources.values()) else {}
        row = f"{obs:8s}"
        for k in sources:
            if k in g:
                a, e = fb_asym(g[k])
                row += f"{a:>13.5f} ±{e:7.5f}"
            else:
                row += f"{'-':>22s}"
        L.append(row)
    L.append("")
    L.append("C-mirror test: lth+(theta) vs lth-(180-theta), chi2/ndf (must be ~1 for any generator)")
    for k, s in sources.items():
        if "lth+" in s["hists"] and "lth-" in s["hists"]:
            gp, gm = on_grid("lth+", group), on_grid("lth-", group)
            if k in gp and k in gm:
                c, n = mirror_chi2(gp[k], gm[k])
                L.append(f"    {k:14s} {c:8.2f}  ({n} bins)")
    txt = "\n".join(L) + "\n"
    with open(path, "w") as f:
        f.write(txt)
    print(txt)


# ── plotting ──────────────────────────────────────────────────────────────────
def zorder(k):
    # CEEX above the Phokhara sets; BabaYaga, dashed, above CEEX, because the
    # two agree to ~0.02% and a solid line would hide one behind the other
    return 6 if k == "babayaga" else 5 if k.startswith("ceex") else 3


def ceex_keys(g):
    return [k for k in g if k.startswith("ceex")]


def draw_distribution(ax, g, legend=True):
    for k, bins in g.items():
        col, ls, lw = sources[k]["style"]
        ax.plot(*make_step(bins), color=col, ls=ls, lw=lw, zorder=zorder(k),
                label=sources[k]["label"] if legend else "_nolegend_")
        xb, lo, hi = make_step_band(bins, [b[2] - b[3] for b in bins],
                                    [b[2] + b[3] for b in bins])
        ax.fill_between(xb, lo, hi, color=col, alpha=0.2, lw=0)
    ref = next(iter(g.values()))
    ax.set_xlim(ref[0][0], ref[-1][1])
    pos = [b[2] for bins in g.values() for b in bins if b[2] > 0]
    if pos and max(pos) / min(pos) > 1e4:
        ax.set_yscale("log")


def draw_ratio(ax, g, nums, den):
    """nums / den on ax. Each numerator carries its own MC error; the
    denominator's error is drawn once, as a band around 1 in its colour."""
    dbins = g[den]
    dvals = [b[2] for b in dbins]
    bounds = []
    for k in nums:
        col, ls, lw = sources[k]["style"]
        r, re_ = compute_ratio([b[2] for b in g[k]], [b[3] for b in g[k]],
                               dvals, [0.0] * len(dvals))
        ax.plot(*make_step_values(g[k], r), color=col, ls=ls, lw=lw, zorder=zorder(k))
        xb, lo, hi = make_step_band(g[k], [x - e for x, e in zip(r, re_)],
                                    [x + e for x, e in zip(r, re_)])
        ax.fill_between(xb, lo, hi, color=col, alpha=0.2, lw=0, zorder=zorder(k) - 0.5)
        bounds += [x for x, d in zip(r, dvals) if d != 0]
    dcol = sources[den]["style"][0]
    rel = [b[3] / b[2] if b[2] else 0.0 for b in dbins]
    xb, lo, hi = make_step_band(dbins, [1 - e for e in rel], [1 + e for e in rel])
    ax.fill_between(xb, lo, hi, color=dcol, alpha=0.18, lw=0, zorder=1)
    ax.axhline(1.0, color=dcol, lw=1.2, zorder=2)
    if bounds:
        q = np.nanpercentile(bounds, [1, 99])
        ax.set_ylim(*compute_ratio_ylimits(list(q), min_half_range=0.005))
    ax.set_xlim(dbins[0][0], dbins[-1][1])


def ratio_panels(g):
    """[(numerators, denominator, y-label)] for the panels this observable
    supports: CEEX / BabaYaga (Phokhara / BabaYaga without CEEX), then
    {CEEX, BabaYaga} / Phokhara."""
    out = []
    ce = ceex_keys(g)
    n1 = bb_nums(list(g))
    if BB in g and n1:
        out.append((n1, BB, PANEL1))
    nums = ce + ([BB] if BB in g else [])
    if REF in g and nums:
        out.append((nums, REF, "X / Phokhara"))
    return out


def plot_obs(obs, group, folder):
    g = on_grid(obs, group)
    panels = ratio_panels(g)
    if not panels:
        return None
    xlabel, ylabel = LABELS.get(obs, (obs, "dsigma/dx"))
    fig = plt.figure(figsize=(7.5, 4.6 + 1.3 * len(panels)), facecolor=BG_COLOR)
    gs = gridspec.GridSpec(1 + len(panels), 1, height_ratios=[2.2] + [1] * len(panels),
                           hspace=0.06, top=0.93, bottom=0.30, left=0.14, right=0.97)
    ax_d = fig.add_subplot(gs[0])
    draw_distribution(ax_d, g)
    style_axis(ax_d, ylabel=ylabel + " [nb/unit]", title=f"{obs}: {xlabel}")
    axes = [ax_d]
    for i, (nums, den, lab) in enumerate(panels):
        ax = fig.add_subplot(gs[1 + i], sharex=ax_d)
        draw_ratio(ax, g, nums, den)
        style_axis(ax, ylabel=lab, xlabel=xlabel if i == len(panels) - 1 else None)
        axes.append(ax)
    for ax in axes[:-1]:
        plt.setp(ax.get_xticklabels(), visible=False)
    xs = [r"$\sigma$ [nb] over this range:"]
    for k, bins in g.items():
        sv, e = integrate_xs(bins)
        xs.append(f"{sources[k]['label']}: {sv:.5f} ± {e:.5f}")
    ax_d.text(0.02, 0.97, "\n".join(xs), transform=ax_d.transAxes, ha="left", va="top",
              fontsize=7, bbox=dict(facecolor="white", edgecolor="black", lw=0.6,
                                    boxstyle="round,pad=0.3", alpha=0.9))
    h, l = ax_d.get_legend_handles_labels()
    ch = [mlines.Line2D([], [], ls="none") for _ in CUTS_TEXT]
    fig.legend(h + ch, l + CUTS_TEXT, loc="lower center", ncol=2, fontsize=8,
               bbox_to_anchor=(0.55, 0.0), frameon=True)
    out = os.path.join(folder, f"pi_kloe_la_{obs}.pdf")
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_overview(obs_list, group, folder, which):
    """One page, one ratio panel per observable. which = 0: CEEX / BabaYaga,
    1: {CEEX, BabaYaga} / Phokhara."""
    rows = []
    for obs in obs_list:
        g = on_grid(obs, group)
        p = [x for x in ratio_panels(g) if x[1] == (BB if which == 0 else REF)]
        if p:
            rows.append((obs, g, p[0]))
    if not rows:
        return None
    nc = 4
    nr = (len(rows) + nc - 1) // nc
    fig, axes = plt.subplots(nr, nc, figsize=(4.2 * nc, 2.6 * nr + 1.2),
                             facecolor=BG_COLOR, squeeze=False)
    used = set()
    for ax, (obs, g, (nums, den, lab)) in zip(axes.flat, rows):
        draw_ratio(ax, g, nums, den)
        used.update(nums + [den])
        style_axis(ax, xlabel=LABELS.get(obs, (obs,))[0], ylabel=lab)
        ax.set_title(obs + ("  (angle)" if obs in ANGLE_OBS else ""), fontsize=11)
    for ax in list(axes.flat)[len(rows):]:
        ax.axis("off")
    keys = [k for k in sources if k in used]
    h = [mlines.Line2D([], [], color=sources[k]["style"][0], ls=sources[k]["style"][1],
                       lw=sources[k]["style"][2]) for k in keys]
    fig.legend(h, [sources[k]["label"] for k in keys], loc="lower center",
               ncol=len(h), fontsize=9, frameon=True)
    fig.suptitle(PANEL1 if which == 0 else
                 f"CEEX and BabaYaga / {sources[REF]['label']}", fontsize=12)
    fig.tight_layout(rect=(0, 0.05, 1, 0.97))
    out = os.path.join(folder, "overview_vs_babayaga.pdf" if which == 0
                       else "overview_vs_phokhara.pdf")
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out


os.makedirs(out_dir, exist_ok=True)
plotted = [o for o in OBS_ORDER if sum(o in s["hists"] for s in sources.values()) >= 2]
print(f"observables in >= 2 sources: {', '.join(plotted)}")
for group, sub in REBIN_VARIANTS:
    folder = os.path.join(out_dir, sub)
    os.makedirs(folder, exist_ok=True)
    for obs in plotted:
        f = plot_obs(obs, group, folder)
        if f and DO_PREVIEW and group == 60 and obs in ANGLE_OBS:
            preview_pdf(f)
    for which in (0, 1):
        f = plot_overview(plotted, group, folder, which)
        if f and DO_PREVIEW and group == 10:
            preview_pdf(f)
    print(f"✅  {sub}: {len(plotted)} observables + overviews → {folder}/")
write_summary(os.path.join(out_dir, "summary.txt"))
