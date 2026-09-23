import glob
import multiprocessing as mp
import os
import re
import math
import sys
from collections import defaultdict

# Base directory to scan: a scratch tree of RUN_CEEX_<seed>_<ecut>/ dirs
# (produced by run.sh). Defaults to the user's scratch dir; pass a
# different path as a positional arg to reuse this on other runs.
# --discard controls the outlier workflow entirely: without it, outliers are
# never even flagged/prompted for and all values go into the average as-is.
# With it, outliers are detected, you're asked whether to drop them from the
# average, and (if dropped) whether to delete/rename the source files on disk.
# --show only controls whether the flagged values themselves (with their
# modified z-score and source file) are printed -- detection/prompting/removal
# behave the same either way.
DISCARD = "--discard" in sys.argv
SHOW = "--show" in sys.argv
_positional = [a for a in sys.argv[1:] if a not in ("--discard", "--show")]
BASEDIR = _positional[0] if _positional else os.path.expanduser("~/scratch")
file_pattern = os.path.join(BASEDIR, "**", "output_*.txt")

# Output dirs are named RUN_CEEX_<seed>_<ecut>/ (see run.sh) — extract the
# ecut so results from different phase-space cuts are never averaged together.
ecut_pattern = re.compile(r"RUN_CEEX_\d+_(\d+)/")


def extract_ecut(filepath):
    m = ecut_pattern.search(filepath)
    return m.group(1) if m else "unknown"


# Regex to match VEGAS entries (per-n breakdown, kept for reference/printing only)
vegas_pattern = re.compile(
    r"\[\+\] n =\s*(\d+)\s*=> I = \(nb\):\s*([0-9Ee+.\-]+)\s*\+/-\s*([0-9Ee+.\-]+)"
)

# Regex to match the per-file "Total cross-section" line
# e.g. " [i] Total cross-section (nb) :    1.0039081491739053   +/-   1.8770168347943088E-006"
total_pattern = re.compile(
    r"Total cross-section \(nb\)\s*:\s*([0-9Ee+.\-]+)\s*\+/-\s*([0-9Ee+.\-]+)"
)

# Loose match for the same line, used only to notice when it's present but
# didn't parse (e.g. a NaN error from a corrupted run) -- total_pattern above
# simply fails to match "NaN"/"Inf", so without this a corrupted total
# vanishes from the average with no warning at all.
total_line_pattern = re.compile(r"Total cross-section \(nb\)\s*:")

NONINTERACTIVE = not sys.stdin.isatty()

# Summary files are written into RUN/ (this script's own directory), regardless
# of which scratch tree (BASEDIR) was scanned for input files. One file per
# ecut, mirroring merge.py's merged_histograms_<ecut>.txt convention.
RUNDIR = os.path.dirname(os.path.abspath(__file__))


def summary_file_for(ecut):
    return os.path.join(RUNDIR, f"average_summary_{ecut}.txt")


# Data structures, keyed by ecut first:
# results_by_ecut[ecut][n] -> per-n VEGAS breakdown (informational only)
# file_counts_by_ecut[ecut][n] -> files contributing to that n
# totals_by_ecut[ecut] -> list of {"value","error","file"}, one entry per
# file — this is the level at which outlier detection runs.
results_by_ecut = defaultdict(lambda: defaultdict(list))
file_counts_by_ecut = defaultdict(lambda: defaultdict(int))
totals_by_ecut = defaultdict(list)

# Scan files
matched_files = glob.glob(file_pattern, recursive=True)
print(f"Found {len(matched_files)} files matching pattern '{file_pattern}'.")

if not matched_files:
    print("ERROR: No files matched. Exiting.")
    sys.exit(1)

# Reading + regex-scanning every line of every output_*.txt (twice, once for
# the VEGAS breakdown and once for the Total line) is the expensive part
# here, and each file is independent of every other -- so parse files in a
# worker pool ("map") and fold the per-file results into the shared
# results_by_ecut/file_counts_by_ecut/totals_by_ecut dicts back here in the
# main process ("reduce"), same split as merge.py. NUM_WORKERS is overridable
# via AVERAGE_JOBS= for when this runs alongside merge.py (see
# post_process.sh), which does the same split and would otherwise double up
# on cores.
NUM_WORKERS = int(os.environ.get("AVERAGE_JOBS", os.cpu_count() or 1))


def _process_file(filepath):
    """
    Parse one output_*.txt file. Runs in a worker process, so it must be
    self-contained (only touches its argument) and side-effect-free (no
    printing, no shared state) -- any messages are returned as strings and
    printed back in the main process afterward, in file order, instead.
    """
    warnings = []
    ecut = extract_ecut(filepath)

    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
    except Exception as e:
        warnings.append(f"ERROR: Cannot read {filepath}: {e}")
        return ecut, [], None, warnings

    # Parse VEGAS per-n values (informational breakdown only)
    vegas = []
    for line in lines:
        match = vegas_pattern.search(line)
        if match:
            try:
                n     = int(match.group(1))
                value = float(match.group(2))
                error = float(match.group(3))
                vegas.append((n, value, error))
            except ValueError:
                warnings.append(f"  Skipping unparsable line: {line.strip()}")

    # Parse the per-file Total cross-section line — this is what outlier
    # detection actually runs on
    total = None
    total_found = False
    for line in lines:
        match = total_pattern.search(line)
        if match:
            total_found = True
            try:
                total = (float(match.group(1)), float(match.group(2)))
            except ValueError:
                warnings.append(f"  Skipping unparsable total line: {line.strip()}")
            break  # only one Total cross-section line expected per file

    # The line is there but didn't match total_pattern at all -- almost
    # always a NaN/Inf value or error from a corrupted run. Surface it
    # instead of letting the file silently disappear from the average.
    if not total_found:
        for line in lines:
            if total_line_pattern.search(line):
                warnings.append(f"  !! Corrupted Total cross-section line in {filepath} "
                                 f"(non-finite value/error) -- excluded from the average: {line.strip()}")
                break

    return ecut, vegas, total, warnings


if NUM_WORKERS > 1 and len(matched_files) > 1:
    with mp.Pool(processes=min(NUM_WORKERS, len(matched_files))) as pool:
        file_results = pool.map(_process_file, matched_files)
else:
    file_results = [_process_file(filepath) for filepath in matched_files]

for filepath, (ecut, vegas, total, warnings) in zip(matched_files, file_results):
    for w in warnings:
        print(w)

    results = results_by_ecut[ecut]
    file_counts = file_counts_by_ecut[ecut]

    # Collect n values present in this valid file, then count it exactly
    # once per n it contributed to
    n_values_in_file = set()
    for n, value, error in vegas:
        results[n].append({"value": value, "error": error, "file": filepath})
        n_values_in_file.add(n)
    for n in n_values_in_file:
        file_counts[n] += 1

    if total is not None:
        value, error = total
        totals_by_ecut[ecut].append({"value": value, "error": error, "file": filepath})


def median(vals):
    s = sorted(vals)
    m = len(s)
    mid = m // 2
    if m % 2 == 0:
        return (s[mid - 1] + s[mid]) / 2
    return s[mid]


def detect_outliers(entries, threshold=3.5):
    """
    Robust outlier detection using the modified z-score (median + MAD).
    Returns list of (entry, modified_z_score) for entries flagged as outliers.
    """
    if len(entries) < 3:
        return []  # not enough data to judge

    vals = [e["value"] for e in entries]
    med = median(vals)
    abs_devs = [abs(v - med) for v in vals]
    mad = median(abs_devs)

    if mad == 0:
        return []

    outliers = []
    for e, v, ad in zip(entries, vals, abs_devs):
        # 0.6745 is the constant that makes MAD comparable to std dev for normal data
        mz = 0.6745 * ad / mad
        if mz > threshold:
            outliers.append((e, mz))
    return outliers


def handle_outlier_files(outlier_files):
    """
    Ask the user whether to delete or rename the on-disk files that produced
    confirmed outliers. outlier_files is a set of filepaths.
    """
    if not outlier_files:
        return

    print(f"\n  The following {len(outlier_files)} file(s) produced the removed outlier(s):")
    for f in sorted(outlier_files):
        print(f"     {f}")

    action = input(
        "  What do you want to do with these files? "
        "[d]elete / [r]ename (append .outlier) / [n]o action: "
    ).strip().lower()

    if action == "d":
        for f in sorted(outlier_files):
            try:
                os.remove(f)
                print(f"  Deleted: {f}")
            except Exception as e:
                print(f"  ERROR deleting {f}: {e}")
    elif action == "r":
        for f in sorted(outlier_files):
            try:
                new_name = f + ".outlier"
                os.rename(f, new_name)
                print(f"  Renamed: {f} -> {new_name}")
            except Exception as e:
                print(f"  ERROR renaming {f}: {e}")
    else:
        print("  Left files untouched on disk.")


def prompt_remove_outliers_for_totals(entries):
    """
    Detect outliers among the per-file TOTAL cross-section values, show them
    to the user with their source file, and ask whether to remove them from
    the average and/or delete/rename the source file.
    Returns the (possibly filtered) list of entries.

    Only called when --discard was passed (see main loop below); in
    non-interactive contexts (e.g. running unattended inside a SLURM job, no
    TTY on stdin) detected outliers are reported but never removed automatically.
    """
    outliers = detect_outliers(entries)
    if not outliers:
        return entries

    if SHOW:
        print("\n  !! Possible outlier(s) detected in TOTAL cross-section !!")
        for entry, mz in outliers:
            print(f"     total={entry['value']:.6g} nb  (modified z-score={mz:.1f})  "
                  f"file={entry['file']}")
    else:
        print(f"\n  !! {len(outliers)} possible outlier(s) detected in TOTAL cross-section "
              f"(pass --show to see values) !!")

    if NONINTERACTIVE:
        print("  Non-interactive run: keeping all values (no files touched).")
        return entries

    answer = input("  Remove these file(s) from the total cross-section average? [y/N]: ").strip().lower()
    if answer == "y":
        outlier_set = {id(e) for e, _ in outliers}
        filtered = [e for e in entries if id(e) not in outlier_set]
        print(f"  Removed {len(entries) - len(filtered)} outlier(s) from the average.")

        outlier_files = {e["file"] for e, _ in outliers}
        handle_outlier_files(outlier_files)

        return filtered
    else:
        print("  Keeping all values.")
        return entries


# Averaging function for the per-n breakdown (unweighted mean of value/error)
def average(entries):
    mean_val = sum(e["value"] for e in entries) / len(entries)
    mean_err = sum(e["error"] for e in entries) / len(entries)
    return mean_val, mean_err


def mean_and_stderr(entries):
    """
    Mean and standard error of the mean across repeated per-file total
    cross-section measurements (these are independent estimates of the same
    quantity, so the scatter between them tells us the uncertainty).
    """
    n = len(entries)
    vals = [e["value"] for e in entries]
    mean_val = sum(vals) / n
    if n > 1:
        variance = sum((v - mean_val) ** 2 for v in vals) / (n - 1)
        stderr = math.sqrt(variance / n)
    else:
        stderr = entries[0]["error"]  # fall back to the single MC error
    return mean_val, stderr


for ecut in sorted(totals_by_ecut.keys()):
    print(f"\n\n################ ecut = 1e-{ecut} ################")

    totals = totals_by_ecut[ecut]
    results = results_by_ecut[ecut]
    file_counts = file_counts_by_ecut[ecut]

    # === Outlier detection & cleanup pass — on TOTAL cross-section ===
    # Gated entirely behind --discard: without it, no detection/prompting
    # happens at all and every value goes into the average as-is.
    if DISCARD:
        print("\n========== OUTLIER CHECK (total cross-section) ==========")
        totals = prompt_remove_outliers_for_totals(totals)

    # Report lines are both printed and written to this ecut's summary file.
    report_lines = []

    def emit(line=""):
        print(line)
        report_lines.append(line)

    # Per-n VEGAS breakdown — informational only, no outlier filtering applied here
    emit("\n========== AVERAGED VEGAS RESULTS (per n, informational) ==========")
    emit(f"{'n':<3} {'Avg (nb)':>15} {'Err (nb)':>15} {'Files':>6}")
    emit("=" * 60)

    for n in sorted(results.keys()):
        mean_val, mean_err = average(results[n])
        count = file_counts[n]
        emit(f"{n:<3} {mean_val:15.6f} {mean_err:15.6f} {count:6d}")
    emit("-" * 60)

    # Total cross section — computed from the (outlier-cleaned) per-file totals
    emit("\n========== TOTAL CROSS SECTION (outlier-cleaned) ==========")
    emit(f"{'Total (nb)':>15} {'StdErr (nb)':>15} {'N files':>8}")
    emit("=" * 55)
    if not totals:
        emit(f"{'--- no data left after removing outliers ---':>15}")
    else:
        total_val, total_stderr = mean_and_stderr(totals)
        emit(f"{total_val:15.6f} {total_stderr:15.6f} {len(totals):8d}")
    emit("=" * 55)

    summary_file = summary_file_for(ecut)
    with open(summary_file, "w") as fout:
        fout.write("\n".join(report_lines) + "\n")
    print(f"\nWrote {summary_file}")
