#!/bin/bash
#SBATCH --job-name=CEEX_LA_NLO_PI
#SBATCH --partition=nodes
#SBATCH --nodes=1
#SBATCH --ntasks=5
#SBATCH --cpus-per-task=1
#SBATCH --mem=5G
#SBATCH --exclude=node025,node029,node051
#SBATCH --output=/users/jpaltrin/scratch/CEEX_PHOKHARA_ANALYSIS/slurm-out/RUN_CEEX/%x_%A_%a.out
#SBATCH --error=/users/jpaltrin/scratch/CEEX_PHOKHARA_ANALYSIS/slurm-out/RUN_CEEX/%x_%A_%a.err
#
# CEEX main, pipig KLOE-LA fixed-order NLO with GoSam (eepipig_noVP_1L_onshell +
# eepipigg): F(pi)=1, no VP -- the configuration of the Phokhara card in
# ../RUN_PHOKHARA/cards/.
#
# Submit through ./submit.sh, which sets RUN_NAME, NEVENTS, ECUTS, --array, --time.
# Task i -> seed 1+(i-1)/#ECUTS, ecut cycling fastest; rank r of seed s runs
# with CEEX seed 100*s+r, so seeds never collide across tasks.
set -euo pipefail
source "$HOME/software/CEEX_PHOKHARA_ANALYSIS/RUN/config.sh"
module load gcc/14.2.0
module load openmpi/5.0.8/gcc-14.2.0
export LD_LIBRARY_PATH="${GOSAM_LIB}:${LD_LIBRARY_PATH:-}"
export OMP_NUM_THREADS=1
cd "$CEEX_ROOT"   # the GoSam process libraries are on a relative rpath

: "${RUN_NAME:?set RUN_NAME (use submit.sh)}"
# the rundir below is rm -rf'd: never let a bad index map onto another task's dir
[[ "${SLURM_ARRAY_TASK_ID:-}" =~ ^[1-9][0-9]*$ ]] || { echo "bad SLURM_ARRAY_TASK_ID='${SLURM_ARRAY_TASK_ID:-}'" >&2; exit 1; }
NPROC=5
NEVENTS=${NEVENTS:-10k}
CUTS=(${ECUTS:-4 5})
idx=$((SLURM_ARRAY_TASK_ID - 1))
seed=$((1 + idx / ${#CUTS[@]}))
ecut=${CUTS[$((idx % ${#CUTS[@]}))]}
rundir="${CEEX_SCRATCH}/${RUN_NAME}/RUN_CEEX_${seed}_${ecut}/"
rm -rf "$rundir"; mkdir -p "$rundir"
echo "[run_ceex] run=${RUN_NAME} task=${SLURM_ARRAY_TASK_ID} seed=${seed} ecut=${ecut} n=${NEVENTS} exe=${CEEX_EXE} @ $(git -C "$CEEX_ROOT" rev-parse --short HEAD) -> ${rundir}"
mpirun -np ${NPROC} --mca pml ob1 --mca btl self,vader "$CEEX_EXE" \
       --process=pipig --scenario=KLOE-LA --NLO \
       --n=${NEVENTS} --seed="${seed}" --emin="1d-${ecut}" --outdir="${rundir}" --uni_bin
echo "[run_ceex] done task=${SLURM_ARRAY_TASK_ID}"
