#!/bin/bash
# Usage: ./submit.sh <run_name> <n_seeds> <nevents> <nmax> [walltime] [seed_offset]
#   e.g. ./submit.sh test10k 30 10000 10000 00:20:00
# nevents (nges) and nmax (nm, the weight-maximum scan) both count events PASSING
# the cuts, at ~1 ms each. The scan only sets the channel split (phokhara_nostop
# never aborts on Mmax < weight), so a quick 10k scan is enough.
# Output: $PHOKHARA_SCRATCH/<run_name>/seed_<k>/. Refuses an existing run name.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
source "$HERE/../config.sh"
NAME=$1; NSEEDS=$2; NEV=$3; NMAX=$4; WALL=${5:-02:00:00}; OFF=${6:-0}
RUNDIR="$PHOKHARA_SCRATCH/$NAME"
[ -e "$RUNDIR" ] && { echo "$RUNDIR exists -- pick another run name or remove it" >&2; exit 1; }
mkdir -p "$RUNDIR"
sbatch --array=1-$NSEEDS --time="$WALL" --job-name="PHOK_$NAME" \
       --export=ALL,RUN_NAME="$NAME",NEVENTS="$NEV",NMAX="$NMAX",SEED_OFFSET="$OFF" "$HERE/run_phokhara.sh"
echo "$(date -Is) $NAME seeds=$NSEEDS nges=$NEV nm=$NMAX wall=$WALL seed_offset=$OFF" >> "$RUNDIR/SUBMITTED.txt"
