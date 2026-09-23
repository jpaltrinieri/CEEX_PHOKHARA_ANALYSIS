#!/bin/bash
# Merge the raw output of one named run into PLOTS/DATA/<run>/.
#
#   ./post_process.sh <run> [ceex|phokhara|all]    (default: all)
#
#   CEEX     $CEEX_SCRATCH/<run>/RUN_CEEX_*      -> PLOTS/DATA/<run>/ceex/merged_histograms_<ecut>.txt
#   Phokhara $PHOKHARA_SCRATCH/<run>/seed_*      -> PLOTS/DATA/<run>/phokhara/NLOFF1_<obs>.csv
#   Either may be absent (e.g. a Phokhara-only run); it is skipped with a note.
#   PLOTS/DATA/<run>/{babayaga,phokhara_ref} are links to the shared reference sets.
#
# Paths come from ../config.sh. merge.py/average.py are unmodified copies of
# CEEX_ANALYSIS/RUN/POST_PROCESS: they write next to themselves, and the
# results are then moved into DATA -- nothing in CEEX_ANALYSIS is touched.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/../config.sh"
RUN=${1:?usage: $0 <run> [ceex|phokhara|all]}
what=${2:-all}
OUT="$PLOTS_DATA/$RUN"
mkdir -p "$OUT"
ln -sfn ../babayaga "$OUT/babayaga"
ln -sfn ../phokhara_ref "$OUT/phokhara_ref"

do_ceex() {
    local src="$CEEX_SCRATCH/$RUN"
    if ! ls -d "$src"/RUN_CEEX_* >/dev/null 2>&1; then echo "[post_process] no CEEX output in $src, skipped"; return; fi
    cd "$HERE"
    rm -f merged_histograms_*.txt average_summary_*.txt
    python3 average.py "$src" < /dev/null
    python3 merge.py "$src" < /dev/null
    rm -rf "$OUT/ceex"; mkdir -p "$OUT/ceex"
    mv merged_histograms_*.txt average_summary_*.txt "$OUT/ceex/"
    echo "$(date -Is) $src" > "$OUT/ceex/SOURCE.txt"
    echo "[post_process] CEEX -> $OUT/ceex/"
}

do_phokhara() {
    local src="$PHOKHARA_SCRATCH/$RUN"
    if ! ls -d "$src"/seed_* >/dev/null 2>&1; then echo "[post_process] no Phokhara output in $src, skipped"; return; fi
    rm -rf "$OUT/phokhara"
    python3 "$HERE/merge_phokhara.py" "$src" "$OUT/phokhara"
    echo "$(date -Is) $src" > "$OUT/phokhara/SOURCE.txt"
}

case "$what" in
    ceex)     do_ceex ;;
    phokhara) do_phokhara ;;
    all)      do_ceex; do_phokhara ;;
    *)        echo "usage: $0 <run> [ceex|phokhara|all]" >&2; exit 1 ;;
esac
