"""
Shared plotting style/constants for the plot_*.py scripts in this directory.

Centralizes the LO/NLO reference colors, the CEEX Emin greyscale palette,
and the common axis cosmetics/utility helpers so every script renders
consistently:
  - LO_COLOR  (orange) for any leading-order reference curve
  - NLO_COLOR (red)    for any next-to-leading-order reference curve
  - get_ecut_colors()  grayscale palette for the CEEX Emin curves
"""
import matplotlib.pyplot as plt
import matplotlib as mpl

# ──────────────────────────────────────────────────────────────────────────────
# Reference colors
# ──────────────────────────────────────────────────────────────────────────────

LO_COLOR = "#e6994d"    # orange -- LO reference curves (MC-MuLE LO, BabaYaga LO, Phokhara LO, ...)
NLO_COLOR = "#cc0000"   # red    -- NLO reference curves (BabaYaga NLO, Phokhara NLO, McMule NLO, ...)
NLOPS_COLOR = "#2f6ea5" # blue   -- NLO+PS reference curves (BabaYaga NLOPSnovp, ...)

BG_COLOR = (1, 1, 1)


# ──────────────────────────────────────────────────────────────────────────────
# Global rcParams
# ──────────────────────────────────────────────────────────────────────────────

def apply_global_style():
    plt.style.use("seaborn-v0_8-whitegrid")
    mpl.rcParams.update({
        "mathtext.fontset": "cm",
        "font.family": "serif",
        "axes.unicode_minus": False,
        "font.size": 12,
        "axes.titlesize": 12,
        "axes.labelsize": 12,
        "legend.fontsize": 11,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
    })


# ──────────────────────────────────────────────────────────────────────────────
# CEEX Emin greyscale palette
# ──────────────────────────────────────────────────────────────────────────────

def get_ecut_colors(n):
    """
    Grayscale palette for the n CEEX ecut curves, assuming they are supplied
    in ascending ecut order (smallest ecut/largest Emin first). Returns light
    gray for the smallest ecut and near-black for the largest ecut (softest
    cutoff, smallest Emin).
    """
    cmap = mpl.colormaps["Greys"]
    if n <= 1:
        return [cmap(0.85)]
    return [cmap(0.15 + 0.70 * i / (n - 1)) for i in range(n)]


def format_ecut_label(ecut):
    try:
        exp = int(ecut)
        return rf"$E_\mathrm{{min}} = 10^{{-{exp}}}$"
    except ValueError:
        return f"Emin={ecut}"


# ──────────────────────────────────────────────────────────────────────────────
# Histogram/step helpers
# ──────────────────────────────────────────────────────────────────────────────
# BabaYaga native-file loading / rebinning (shared with plot_kloe_la_bb_pi.py's
# local copies of the same two functions).
# ──────────────────────────────────────────────────────────────────────────────

def load_babayaga_file(path):
    """
    Read a 'x_l , NLO , dNLO' BabaYaga file (a uniformly-binned native
    differential distribution: only the left edge is stored per row, and
    the common bin width is taken from the first two rows and applied to
    every bin, including the last).
    """
    lefts, vals, errs = [], [], []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.lower().startswith("x_l"):
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) != 3:
                continue
            try:
                lefts.append(float(parts[0]))
                vals.append(float(parts[1]))
                errs.append(float(parts[2]))
            except ValueError:
                continue
    if len(lefts) < 2:
        return []
    width = lefts[1] - lefts[0]
    return [(lefts[i], lefts[i] + width, vals[i], errs[i])
            for i in range(len(lefts))]


def rebin_onto(src_bins, target_bins):
    """
    Project `src_bins` (a differential distribution) onto the bin edges of
    `target_bins` using an area-weighted overlap integral:

        value_target = (1/w_target) * sum_i value_i * overlap(i, target)

    Exact when the target edges are a coarsening/subset of the source
    edges, and the natural linear interpolation of the integral otherwise.
    Errors are propagated in quadrature (source bins treated as
    independent). Target bins not covered by the source get 0.
    """
    out = []
    j = 0
    for tlo, thi, _, _ in target_bins:
        w = thi - tlo
        area, err2 = 0.0, 0.0
        while j < len(src_bins) and src_bins[j][1] <= tlo:
            j += 1
        k = j
        while k < len(src_bins) and src_bins[k][0] < thi:
            slo, shi, val, err = src_bins[k]
            ov = min(shi, thi) - max(slo, tlo)
            if ov > 0:
                area += val * ov
                err2 += (err * ov) ** 2
            k += 1
        out.append((tlo, thi, area / w if w > 0 else 0.0,
                    err2 ** 0.5 / w if w > 0 else 0.0))
    return out


# ──────────────────────────────────────────────────────────────────────────────

def make_step(bins):
    x, y = [], []
    for xmin, xmax, val, _ in bins:
        x.extend([xmin, xmax])
        y.extend([val, val])
    return x, y


def make_step_values(bins, values):
    """Like make_step, but the plotted value per bin is taken from `values`
    (e.g. a ratio) rather than from the bin tuple itself. Only the bin edges
    (xmin, xmax) are used from `bins`."""
    x, y = [], []
    for (xmin, xmax, _, _), v in zip(bins, values):
        x.extend([xmin, xmax])
        y.extend([v, v])
    return x, y


def make_step_band(bins, lower_vals, upper_vals):
    """Like make_step_values, but expands two parallel per-bin value lists
    (e.g. a ratio band's lower/upper edges) into histogram-style step
    coordinates sharing one x array, for use with ax.fill_between — so the
    shaded band follows the bin edges instead of linearly interpolating
    between bin centres."""
    x, y_lo, y_hi = [], [], []
    for (xmin, xmax, _, _), lo, hi in zip(bins, lower_vals, upper_vals):
        x.extend([xmin, xmax])
        y_lo.extend([lo, lo])
        y_hi.extend([hi, hi])
    return x, y_lo, y_hi


def integrate_xs(bins):
    total, err2 = 0.0, 0.0
    for xmin, xmax, val, err in bins:
        w = xmax - xmin
        total += val * w
        err2 += (err * w) ** 2
    return total, err2 ** 0.5


def compute_ratio(heights, errors, ref_vals, ref_errs):
    ratio, ratio_err = [], []
    for val, err, ref, ref_err in zip(heights, errors, ref_vals, ref_errs):
        if ref == 0.0 and val == 0.0:
            r, r_e = 1.0, 0.0
        elif ref != 0:
            r = val / ref
            r_e = r * ((err / val) ** 2 + (ref_err / ref) ** 2) ** 0.5 if val != 0 else 0.0
        else:
            r, r_e = 0.0, 0.0
        ratio.append(r)
        ratio_err.append(r_e)
    return ratio, ratio_err


def compute_ratio_ylimits(bound_values, pad_frac=0.15, min_half_range=0.001):
    """
    Auto-detect sensible y-limits for a ratio panel from a collection of
    ratio +/- error boundary values.

    - Ignores non-finite values.
    - Adds symmetric padding around the observed [min, max] range.
    - Enforces a minimum half-range around 1.0 so a perfectly flat ratio
      (e.g. all values == 1) still gets a sane, non-degenerate window.
    """
    finite_vals = [v for v in bound_values if v == v and abs(v) != float("inf")]

    if not finite_vals:
        return 1.0 - min_half_range, 1.0 + min_half_range

    ymin = min(finite_vals)
    ymax = max(finite_vals)

    # Always include the ratio=1 reference line in the window.
    ymin = min(ymin, 1.0)
    ymax = max(ymax, 1.0)

    half_range = max((ymax - ymin) / 2.0, min_half_range)
    center = (ymax + ymin) / 2.0

    half_range *= (1.0 + pad_frac)

    return center - half_range, center + half_range


# ──────────────────────────────────────────────────────────────────────────────
# Axis cosmetics
# ──────────────────────────────────────────────────────────────────────────────

def style_axis(ax, xlabel=None, ylabel=None, title=None, log=False):
    """Apply the standard grid/ticks/spine cosmetics shared by every panel."""
    if title:
        ax.set_title(title)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.grid(True, linestyle="--", linewidth=0.7, alpha=0.5)
    ax.minorticks_on()
    ax.grid(which="minor", linestyle=":", linewidth=0.5, alpha=0.3)
    ax.tick_params(direction="in", top=True, right=True)
    for spine in ax.spines.values():
        spine.set_linewidth(1)
    if log:
        ax.set_yscale("log")
