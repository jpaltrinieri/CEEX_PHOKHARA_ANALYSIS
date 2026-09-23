#!/bin/bash
# Usage: ./submit.sh <run_name> <n_seeds> <nevents> [walltime] [ecuts]
#   e.g. ./submit.sh test10k 30 10k 00:30:00
#        ./submit.sh prod100k 30 100k 02:00:00 "4 5"
#        EXE=$HOME/software/CEEX-main/MC_<tag> CEEX_NPH_HISTOS=1 ./submit.sh ...   # tagged binary, per-nph histograms
# One array task per (seed, ecut), 5 MPI ranks each, --n=<nevents> per rank.
# Output: $CEEX_SCRATCH/<run_name>/RUN_CEEX_<seed>_<ecut>/. Refuses an existing run name.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
source "$HERE/../config.sh"
EXE=${EXE:-$CEEX_EXE}; [ -x "$EXE" ] || { echo "no executable $EXE" >&2; exit 1; }
NAME=$1; NSEEDS=$2; NEV=$3; WALL=${4:-02:00:00}; ECUTS=${5:-4 5}
RUNDIR="$CEEX_SCRATCH/$NAME"
[ -e "$RUNDIR" ] && { echo "$RUNDIR exists -- pick another run name or remove it" >&2; exit 1; }
mkdir -p "$RUNDIR"
NCUTS=$(wc -w <<< "$ECUTS")
sbatch --array=1-$((NSEEDS * NCUTS))%29 --time="$WALL" --job-name="CEEX_$NAME" \
       --export=ALL,RUN_NAME="$NAME",NEVENTS="$NEV",ECUTS="$ECUTS",EXE="$EXE" "$HERE/run_ceex.sh"
echo "$(date -Is) $NAME seeds=$NSEEDS n=$NEV ecuts='$ECUTS' wall=$WALL exe=$EXE nph_histos=${CEEX_NPH_HISTOS:-0} @ $(git -C "$CEEX_ROOT" rev-parse --short HEAD)" >> "$RUNDIR/SUBMITTED.txt"
