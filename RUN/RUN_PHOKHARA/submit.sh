#!/bin/bash
# Usage: ./submit.sh <run_name> <n_seeds> <nevents> <nmax> [walltime] [seed_offset]
#   e.g. ./submit.sh test10k 30 10000 10000 00:20:00
#        APPEND=1 ./submit.sh prod500k 270 500000 10000 01:00:00 230   # add seeds 231-500
#        CARD=cards/<variant>.template.dat ./submit.sh ...   # another card (default: config.sh)
#        EXE=src/phokhara_<tag> ./submit.sh ...              # a variant binary (variants/build.sh)
# nevents (nges) and nmax (nm, the weight-maximum scan) both count events PASSING
# the cuts, at ~1 ms each. The scan only sets the channel split (phokhara_nostop
# never aborts on Mmax < weight), so a quick 10k scan is enough.
# Output: $PHOKHARA_SCRATCH/<run_name>/seed_<k>/, seeds offset+1 .. offset+n_seeds.
# Refuses an existing run name, unless APPEND=1: then seeds are added to it, the
# same nevents/nmax as the run's first submission are required (the merge is a
# plain mean over seeds), and no seed number may already exist.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
source "$HERE/../config.sh"
CARD=$(readlink -f "${CARD:-$PHOKHARA_CARD}"); [ -f "$CARD" ] || { echo "no card $CARD" >&2; exit 1; }
EXE=$(readlink -f "${EXE:-$PHOKHARA_EXE}"); [ -x "$EXE" ] || { echo "no executable $EXE" >&2; exit 1; }
NAME=$1; NSEEDS=$2; NEV=$3; NMAX=$4; WALL=${5:-02:00:00}; OFF=${6:-0}
RUNDIR="$PHOKHARA_SCRATCH/$NAME"
if [ "${APPEND:-0}" = 1 ]; then
    [ -d "$RUNDIR" ] || { echo "APPEND=1: $RUNDIR does not exist" >&2; exit 1; }
    first=$(head -1 "$RUNDIR/SUBMITTED.txt")
    grep -q "nges=$NEV nm=$NMAX " <<< "$first" \
        || { echo "APPEND=1: nges/nm differ from the run's first submission: $first" >&2; exit 1; }
    for s in $(seq $((OFF + 1)) $((OFF + NSEEDS))); do
        [ -e "$RUNDIR/seed_$s" ] && { echo "APPEND=1: $RUNDIR/seed_$s already exists" >&2; exit 1; }
    done
else
    [ -e "$RUNDIR" ] && { echo "$RUNDIR exists -- pick another run name, remove it, or APPEND=1" >&2; exit 1; }
    mkdir -p "$RUNDIR"
fi
sbatch --array=1-$NSEEDS --time="$WALL" --job-name="PHOK_$NAME" \
       --export=ALL,RUN_NAME="$NAME",NEVENTS="$NEV",NMAX="$NMAX",SEED_OFFSET="$OFF",CARD="$CARD",EXE="$EXE" "$HERE/run_phokhara.sh"
echo "$(date -Is) $NAME seeds=$NSEEDS nges=$NEV nm=$NMAX wall=$WALL seed_offset=$OFF card=$(basename "$CARD") exe=$(basename "$EXE")${APPEND:+ append}" >> "$RUNDIR/SUBMITTED.txt"
