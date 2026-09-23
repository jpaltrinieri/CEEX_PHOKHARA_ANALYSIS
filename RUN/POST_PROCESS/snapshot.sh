#!/bin/bash
# Snapshot the FINISHED part of a run that is still in flight, under a new run
# name, so it can be merged and plotted without touching the original:
#
#   ./snapshot.sh <src_run> <dst_run>      e.g. ./snapshot.sh prod100k test100k
#
# Links (does not copy) into $CEEX_SCRATCH/<dst_run>/ every RUN_CEEX_* task of
# <src_run> whose ranks have all printed "Generation time" (i.e. finished), and
# into $PHOKHARA_SCRATCH/<dst_run>/ every seed_* with a done.txt. Then run
#   ./post_process.sh <dst_run> && (cd ../../PLOTS && make plot RUN=<dst_run>)
# Refuses an existing <dst_run>.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/../config.sh"
SRC=${1:?usage: $0 <src_run> <dst_run>}; DST=${2:?usage: $0 <src_run> <dst_run>}

nc=0; nct=0
if [ -d "$CEEX_SCRATCH/$SRC" ]; then
    [ -e "$CEEX_SCRATCH/$DST" ] && { echo "$CEEX_SCRATCH/$DST exists" >&2; exit 1; }
    mkdir -p "$CEEX_SCRATCH/$DST"
    for d in "$CEEX_SCRATCH/$SRC"/RUN_CEEX_*/; do
        nct=$((nct+1))
        outs=("$d"output_*.txt)
        [ -e "${outs[0]}" ] || continue
        ok=1; for f in "${outs[@]}"; do grep -q 'Generation time' "$f" || { ok=0; break; }; done
        [ $ok = 1 ] && { ln -s "${d%/}" "$CEEX_SCRATCH/$DST/$(basename "${d%/}")"; nc=$((nc+1)); }
    done
fi
np=0; npt=0
if [ -d "$PHOKHARA_SCRATCH/$SRC" ]; then
    [ -e "$PHOKHARA_SCRATCH/$DST" ] && { echo "$PHOKHARA_SCRATCH/$DST exists" >&2; exit 1; }
    mkdir -p "$PHOKHARA_SCRATCH/$DST"
    for d in "$PHOKHARA_SCRATCH/$SRC"/seed_*/; do
        npt=$((npt+1))
        [ -f "$d/done.txt" ] && { ln -s "${d%/}" "$PHOKHARA_SCRATCH/$DST/$(basename "${d%/}")"; np=$((np+1)); }
    done
fi
msg="$(date -Is) snapshot of $SRC: CEEX $nc/$nct tasks finished, Phokhara $np/$npt seeds finished"
for s in "$CEEX_SCRATCH/$DST" "$PHOKHARA_SCRATCH/$DST"; do [ -d "$s" ] && echo "$msg" > "$s/SNAPSHOT.txt"; done
echo "[snapshot] $msg"
