#!/bin/bash
# Take the CEEX outputs that check_total.sh flags out of a run, reversibly:
#
#   ./quarantine.sh <run> [check_total options, e.g. -n 5 -e 10]
#
# For every flagged $CEEX_SCRATCH/<run>/RUN_CEEX_<s>_<e>/output_<r>.txt:
#   * real task directory: the file is MOVED to $CEEX_SCRATCH/<run>_excluded/RUN_CEEX_<s>_<e>/
#   * task that is a link (a snapshot.sh run): the link is replaced by a real
#     directory of links to the task's other ranks; the source run is not touched.
# Each action is appended to $CEEX_SCRATCH/<run>_excluded/EXCLUDED.txt. To undo,
# move the files back (or, for a snapshot, re-link the task directory).
# Only run it on finished tasks: check_total.sh only sees outputs that already
# print their "Total cross-section", so rerun it once a production has finished.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/../config.sh"
RUN=${1:?usage: $0 <run> [check_total options]}; shift
SRC="$CEEX_SCRATCH/$RUN"; EXC="$CEEX_SCRATCH/${RUN}_excluded"
[ -d "$SRC" ] || { echo "no such run: $SRC" >&2; exit 1; }

report=$("$HERE/check_total.sh" -l "$@" "$SRC" || true)
echo "$report"
mapfile -t BAD < <(grep -oE '^RUN_CEEX_[0-9]+_[0-9]+/output_[0-9]+\.txt' <<< "$report")
[ ${#BAD[@]} -eq 0 ] && { echo "[quarantine] nothing to exclude"; exit 0; }

mkdir -p "$EXC"
for rel in "${BAD[@]}"; do
    task=${rel%%/*}; file=${rel##*/}; tdir="$SRC/$task"
    line=$(grep -F "$rel" <<< "$report" | tr -s ' ')
    if [ -L "$tdir" ]; then
        target=$(readlink -f "$tdir")
        rm "$tdir"; mkdir "$tdir"
        for f in "$target"/output_*.txt; do
            [ "$(basename "$f")" = "$file" ] || ln -s "$f" "$tdir/$(basename "$f")"
        done
        echo "$(date -Is) unlinked $rel (snapshot of $target) :: $line" >> "$EXC/EXCLUDED.txt"
    elif [ -f "$tdir/$file" ] && [ ! -L "$tdir/$file" ]; then
        mkdir -p "$EXC/$task"; mv "$tdir/$file" "$EXC/$task/$file"
        echo "$(date -Is) moved $rel -> $EXC/$task/ :: $line" >> "$EXC/EXCLUDED.txt"
    elif [ -L "$tdir/$file" ]; then
        rm "$tdir/$file"
        echo "$(date -Is) unlinked $rel :: $line" >> "$EXC/EXCLUDED.txt"
    fi
done
echo "[quarantine] ${#BAD[@]} output(s) excluded from $RUN; log: $EXC/EXCLUDED.txt"
