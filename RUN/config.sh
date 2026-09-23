# Paths for the CEEX-vs-Phokhara comparison: KLOE-LA, pi+pi-gamma, fixed-order NLO,
# F(pi)=1, no VP. Every script in RUN/ sources this; nothing else holds a path.
# (#SBATCH lines are parsed before bash runs, so the slurm-out paths in the two
# job scripts are hardcoded there too.)

ANALYSIS_ROOT="$HOME/software/CEEX_PHOKHARA_ANALYSIS"

# CEEX main-branch worktree and the frozen binary the jobs run. Never relink
# CEEX_EXE while an array is in flight; build a new tagged binary instead.
CEEX_ROOT="$HOME/software/CEEX-main"
CEEX_EXE="$CEEX_ROOT/MC_mpi"
GOSAM_LIB="$HOME/software/local/gosam3/lib64/GoSam"

# PHOKHARA 10.0 snapshot (built with the KLOE-I cuts) and the runcard template.
PHOKHARA_DIR="$ANALYSIS_ROOT/RUN/RUN_PHOKHARA"
PHOKHARA_EXE="$PHOKHARA_DIR/src/phokhara_nostop"   # Mmax<weight stops disabled (weighted histograms only); src/phokhara is the unpatched build
PHOKHARA_CARD="$PHOKHARA_DIR/cards/input_KLOE-LA_pipi_NLO_noVP_FF1.template.dat"

# Raw output, one directory per named run:
#   $CEEX_SCRATCH/<run>/RUN_CEEX_<seed>_<ecut>/output_<rank>.txt
#   $PHOKHARA_SCRATCH/<run>/seed_<k>/{input.dat,phokhara.out,NLOFF1.dat,done.txt}
SCRATCH_ROOT="$HOME/scratch/CEEX_PHOKHARA_ANALYSIS"
CEEX_SCRATCH="$SCRATCH_ROOT/CEEX"
PHOKHARA_SCRATCH="$SCRATCH_ROOT/PHOKHARA"

# Merged data and plots, one directory per named run.
PLOTS_DATA="$ANALYSIS_ROOT/PLOTS/DATA"
RESULTS_DIR="$ANALYSIS_ROOT/RESULTS"
