import glob
import multiprocessing as mp
import os
import re
import sys
from collections import defaultdict

import numpy as np

# Base directory to scan: a scratch tree of RUN_CEEX_<seed>_<ecut>/ dirs
# (produced by run.sh). Defaults to the user's scratch dir; pass a
# different path as a positional arg to reuse this on other runs.
# --discard controls the ridiculous-negative-bin workflow: bins are always
# checked and flagged, but you're only prompted to drop the offending file
# from the merge (and optionally delete/rename it on disk) when --discard
# is passed. Without it, flagged files are still merged in as-is.
# --show only controls whether the flagged bin values themselves are printed
# -- detection/prompting/exclusion behave the same either way.
DISCARD = "--discard" in sys.argv
SHOW = "--show" in sys.argv
_positional = [a for a in sys.argv[1:] if a not in ("--discard", "--show")]
BASEDIR = _positional[0] if _positional else os.path.expanduser("~/scratch")
all_files = glob.glob(os.path.join(BASEDIR, "**", "output_*.txt"), recursive=True)
print(f"Found {len(all_files)} files.")

# Output dirs are named RUN_CEEX_<seed>_<ecut>/ (see run.sh) — extract the
# ecut so histograms from different phase-space cuts are never merged together.
ecut_pattern = re.compile(r"RUN_CEEX_\d+_(\d+)/")


def extract_ecut(filepath):
    m = ecut_pattern.search(filepath)
    return m.group(1) if m else "unknown"


NONINTERACTIVE = not sys.stdin.isatty()

# A bin is flagged as a "ridiculous" negative if it's negative by far more
# than its own MC error could plausibly explain. Small negative excursions
# around zero are normal (MC subtraction/statistical noise); this is about
# catching corrupted/broken files, not ordinary fluctuations.
RIDICULOUS_NEG_SIGMA = 10
RIDICULOUS_NEG_ABS_FLOOR = 1e-30  # ignore negatives this close to zero (float noise)


def is_ridiculous_negative(val, err):
    if val >= 0 or abs(val) < RIDICULOUS_NEG_ABS_FLOOR:
        return False
    if err > 0:
        return abs(val) > RIDICULOUS_NEG_SIGMA * err
    return True  # meaningfully negative with a zero (or bogus) error bar


def find_ridiculous_negative_bins(file_hists):
    """
    Scan every histogram/bin parsed from one file. Returns a list of
    (hist_name, xmin, xmax, val, err) tuples for bins that look broken
    rather than just statistically noisy.
    """
    flagged = []
    for hist_name, bins in file_hists.items():
        for xmin, xmax, val, err in bins:
            if is_ridiculous_negative(val, err):
                flagged.append((hist_name, xmin, xmax, val, err))
    return flagged


def median(vals):
    s = sorted(vals)
    m = len(s)
    mid = m // 2
    if m % 2 == 0:
        return (s[mid - 1] + s[mid]) / 2
    return s[mid]


# A single anomalously-weighted MC event (CEEX weights can be signed) can
# blow up a bin's value AND its error together in just one file -- that bin
# is self-consistent (the value sits well within its own inflated error bar),
# so is_ridiculous_negative never sees it, yet it towers over every other
# file's value/error at that exact bin. Catch it by comparing each file's
# per-bin value/error against every other file's at the same (histogram, bin
# index) for this ecut, instead of checking each file only against itself.
#
# This deliberately is NOT a median+MAD z-score: at many bins nearly every
# file agrees to within a tiny MAD, so even an utterly ordinary file (one
# with modestly higher per-file noise, still well inside typical run-to-run
# scatter) scores as a huge "z" there and floods the report with harmless
# bins. A single bad event's contribution is not modestly larger, it is
# many *orders of magnitude* off -- so instead we compare each file's
# value/error to the peer *median error* directly (the typical MC noise on
# one file's estimate of this bin) and only flag deviations of
# PEER_OUTLIER_RATIO times that or more, which ordinary statistical scatter
# never reaches but a single dominant-weight event trivially does.
PEER_OUTLIER_RATIO = 200
PEER_OUTLIER_MIN_PEERS = 5  # need this many files at a bin before judging
PEER_OUTLIER_ERR_FLOOR = 1e-12  # guard against dividing by a ~0 median error


def find_peer_outlier_bins(parsed, ecut):
    """
    Compare every file's per-bin (value, error) against every other file's
    at that same (histogram, bin index) for this ecut. Returns
    {filepath: [(hist_name, xmin, xmax, val, err), ...]} for bins that stick
    out from their peers far beyond ordinary MC scatter.

    Grouped and compared with numpy (one (n_files, n_bins) array per
    histogram) rather than a plain-Python {(hist,bin): [(file,val,err),...]}
    dict -- that dict effectively duplicates the entire per-ecut dataset a
    second time (every bin of every file, again), which is what pushed this
    script over the edge on a big scratch tree.
    """
    by_hist = defaultdict(list)  # hist_name -> [(filepath, arr), ...]
    for filepath, file_ecut, file_hists in parsed:
        if file_ecut != ecut:
            continue
        for hist_name, arr in file_hists.items():
            by_hist[hist_name].append((filepath, arr))

    flagged = defaultdict(set)
    for hist_name, entries in by_hist.items():
        if len(entries) < PEER_OUTLIER_MIN_PEERS:
            continue
        vals = np.stack([arr[:, 2] for _, arr in entries])  # (n_files, n_bins)
        errs = np.stack([arr[:, 3] for _, arr in entries])
        med_val = np.median(vals, axis=0)
        med_err = np.median(errs, axis=0)
        denom = np.maximum(med_err, PEER_OUTLIER_ERR_FLOOR)
        outlier = (errs > PEER_OUTLIER_RATIO * denom) | (np.abs(vals - med_val) > PEER_OUTLIER_RATIO * denom)
        for file_idx, bin_idx in zip(*np.nonzero(outlier)):
            filepath, arr = entries[file_idx]
            xmin, xmax, val, err = arr[bin_idx]
            flagged[filepath].add((hist_name, float(xmin), float(xmax), float(val), float(err)))
    return {fp: sorted(bins_) for fp, bins_ in flagged.items()}


def parse_file(filepath):
    """
    Parse one output_*.txt file into {histogram_name: ndarray[(xmin,xmax,val,err), ...]}.

    Bins accumulate as plain Python lists while a histogram block is being
    read (cheap -- one file's worth at a time) and get converted to a single
    compact float64 array per histogram at flush time. Holding thousands of
    files' worth of *that* long-term (in the caller's `parsed` list) as
    numpy arrays rather than Python tuples is what keeps the whole scratch
    tree's worth of bins from ballooning past the machine's memory limit.
    """
    file_hists = {}

    with open(filepath) as f:
        lines = f.readlines()

    current_hist = None
    bins = []

    def flush():
        if current_hist is not None and bins:
            arr = np.array(bins, dtype=np.float64)
            if current_hist in file_hists:
                # Matches the old list .extend() behavior if the same
                # histogram name appears in more than one block in a file.
                file_hists[current_hist] = np.vstack([file_hists[current_hist], arr])
            else:
                file_hists[current_hist] = arr

    for line in lines:
        line = line.strip()
        if line.startswith("Histogram:"):
            flush()
            current_hist = line[len("Histogram:"):].strip()
            bins = []
        elif current_hist:
            if line == "" or line.startswith("Integral"):
                flush()
                current_hist = None
                bins = []
            else:
                parts = line.split()
                if len(parts) == 4:
                    try:
                        xmin, xmax, val, err = map(float, parts)
                        bins.append((xmin, xmax, val, err))
                    except ValueError:
                        pass

    return file_hists


def merge_into(data, file_hists, filepath):
    """Accumulate one file's histograms into the running per-ecut sums."""
    for hist_name, bins in file_hists.items():
        hist_data = data.setdefault(hist_name, [])
        if not hist_data:
            hist_data.extend([(xmin, xmax, val, err**2, 1) for (xmin, xmax, val, err) in bins])
        else:
            for i, (xmin, xmax, val, err) in enumerate(bins):
                hxmin, hxmax, hval, herr2, hcount = hist_data[i]
                if abs(hxmin - xmin) > 1e-12 or abs(hxmax - xmax) > 1e-12:
                    raise ValueError(f"Bin mismatch in {hist_name} at file {filepath}")
                hist_data[i] = (hxmin, hxmax, hval + val, herr2 + err**2, hcount + 1)


def handle_ridiculous_file(filepath, flagged):
    """
    Flag a file with ridiculous negative bin(s). If --discard is set and
    stdin is interactive, ask whether to drop it from the merge and what to
    do with it on disk. Returns True if the file should be EXCLUDED from the
    merge, False if it should still be merged in as normal.
    """
    if SHOW:
        print(f"\n  !! Anomalous bin value(s) detected in {filepath} !!")
        for hist_name, xmin, xmax, val, err in flagged:
            print(f"     {hist_name}: bin [{xmin:.6g}, {xmax:.6g}] value={val:.6g} +/- {err:.6g}")

    if not DISCARD:
        return False

    if NONINTERACTIVE:
        print("  Non-interactive run: keeping file in the merge (no files touched).")
        return False

    answer = input("  Exclude this file from the merge? [y/N]: ").strip().lower()
    if answer != "y":
        print("  Keeping file in the merge.")
        return False

    action = input(
        "  What do you want to do with this file on disk? "
        "[d]elete / [r]ename (append .outlier) / [n]o action: "
    ).strip().lower()
    if action == "d":
        try:
            os.remove(filepath)
            print(f"  Deleted: {filepath}")
        except Exception as e:
            print(f"  ERROR deleting {filepath}: {e}")
    elif action == "r":
        try:
            new_name = filepath + ".outlier"
            os.rename(filepath, new_name)
            print(f"  Renamed: {filepath} -> {new_name}")
        except Exception as e:
            print(f"  ERROR renaming {filepath}: {e}")
    else:
        print("  Left file untouched on disk.")

    return True


# Parsing (reading + splitting/float-converting every line of every
# output_*.txt) is the expensive, embarrassingly-parallel part of this
# script -- each file is parsed completely independently -- so it's farmed
# out across worker processes here ("map"). What used to make holding every
# file's result in `parsed` afterward infeasible on a big scratch tree
# (several GB of plain-Python (xmin,xmax,val,err) tuples for a few thousand
# files) is fixed at the source: parse_file() above now returns compact
# numpy arrays instead, so the full gather back in this one process (the
# "reduce"/remerge below, same as before) comfortably fits in memory.
# NUM_WORKERS is overridable via MERGE_JOBS= for when this runs alongside
# average.py (see post_process.sh), which does the same split and would
# otherwise double up on cores.
NUM_WORKERS = int(os.environ.get("MERGE_JOBS", os.cpu_count() or 1))


def _parse_one(filepath):
    return (filepath, extract_ecut(filepath), parse_file(filepath))


# Parse every file up front -- the peer-outlier check below needs every
# file's bins for an ecut available before it can judge any single one of them.
if NUM_WORKERS > 1 and len(all_files) > 1:
    with mp.Pool(processes=min(NUM_WORKERS, len(all_files))) as pool:
        parsed = pool.map(_parse_one, all_files)
else:
    parsed = [_parse_one(filepath) for filepath in all_files]

self_flagged = {}
for filepath, ecut, file_hists in parsed:
    f = find_ridiculous_negative_bins(file_hists)
    if f:
        self_flagged[filepath] = f

peer_flagged = {}
for ecut in {ecut for _, ecut, _ in parsed}:
    peer_flagged.update(find_peer_outlier_bins(parsed, ecut))

# Structure: { ecut : { histogram_name : [ (xmin, xmax, sum_val, sum_err2, count) ] } }
data_by_ecut = {}

for filepath, ecut, file_hists in parsed:
    flagged = self_flagged.get(filepath, []) + peer_flagged.get(filepath, [])
    if flagged and handle_ridiculous_file(filepath, flagged):
        continue

    data = data_by_ecut.setdefault(ecut, {})
    merge_into(data, file_hists, filepath)

# Write merged histograms into RUN/ (this script's own directory), regardless
# of which scratch tree (BASEDIR) was scanned for input files. One file per
# ecut, named merged_histograms_<ecut>.txt (matches the naming PLOTS/plot_histos.py
# already expects to pull the Emin label from).
RUNDIR = os.path.dirname(os.path.abspath(__file__))

for ecut, data in sorted(data_by_ecut.items()):
    filename = os.path.join(RUNDIR, f"merged_histograms_{ecut}.txt")
    with open(filename, "w") as fout:
        for hist, bins in data.items():
            fout.write(f"Histogram:{hist}\n")
            for xmin, xmax, val_sum, err2_sum, count in bins:
                val_avg = val_sum / count
                err_avg = (err2_sum ** 0.5) / count
                fout.write(f" {xmin:.17e} {xmax:.17e} {val_avg:.17e} {err_avg:.17e}\n")
            fout.write("\n")
    print(f"Wrote {filename}")

print("Merging and averaging done.")
