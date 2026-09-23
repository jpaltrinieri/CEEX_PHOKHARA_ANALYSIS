#!/bin/bash
# Build the T4 driver t4_ceex against CEEX-main's MPI objects (no change to CEEX-main):
# compile flags and link line are taken from CEEX-main/build_nphsplit.log, with MC.o
# replaced by t4_ceex.o. Output: ./t4_ceex (run it from $CEEX_ROOT, see t4_ceex.f90).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
source "$HERE/../../config.sh"
LOG="$CEEX_ROOT/build_nphsplit.log"
cc=$(grep -o 'mpif90[^;]* -c [^ ]*MC.f -o [^ ]*MC.o' "$LOG" | head -1)
cc=${cc/ -J$CEEX_ROOT\/build\/mpi / -J$HERE }
cc=${cc/ -c MC.f -o $CEEX_ROOT\/build\/mpi\/MC.o/ -c $HERE/t4_ceex.f90 -o $HERE/t4_ceex.o}
(cd "$CEEX_ROOT" && eval "$cc")
ld=$(grep -m1 "mpif90 .* -o $CEEX_ROOT/MC_nphsplit " "$LOG")
ld=${ld/ -o $CEEX_ROOT\/MC_nphsplit / -o $HERE/t4_ceex }
ld=${ld/ $CEEX_ROOT\/build\/mpi\/MC.o / $HERE/t4_ceex.o }
[[ "$ld" == *"$HERE/t4_ceex.o"* ]] || { echo "MC.o not found in link line" >&2; exit 1; }
(cd "$CEEX_ROOT" && eval "$ld")
echo "[build] $HERE/t4_ceex"
