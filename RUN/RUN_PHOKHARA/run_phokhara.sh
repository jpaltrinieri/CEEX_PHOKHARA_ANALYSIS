#!/bin/bash
#SBATCH --job-name=PHOK_LA_NLO_PI
#SBATCH --partition=nodes
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --exclude=node025,node029,node051
#SBATCH --output=/users/jpaltrin/scratch/CEEX_PHOKHARA_ANALYSIS/slurm-out/RUN_PHOKHARA/%x_%A_%a.out
#SBATCH --error=/users/jpaltrin/scratch/CEEX_PHOKHARA_ANALYSIS/slurm-out/RUN_PHOKHARA/%x_%A_%a.err
#
# One PHOKHARA seed = one array task. Submit through ./submit.sh, which sets
# RUN_NAME, NEVENTS, NMAX, SEED_OFFSET, --array and --time.
set -u
source "$HOME/software/CEEX_PHOKHARA_ANALYSIS/RUN/config.sh"
: "${RUN_NAME:?set RUN_NAME (use submit.sh)}"
SEED=$(( SEED_OFFSET + SLURM_ARRAY_TASK_ID ))
D=$PHOKHARA_SCRATCH/$RUN_NAME/seed_$SEED
mkdir -p "$D" && cd "$D" || exit 1
cp $PHOKHARA_DIR/src/const_and_model_paramall10.0.dat $PHOKHARA_DIR/src/vpol_all_bare_sum_v2.9.dat \
   $PHOKHARA_DIR/src/vpol_bare_lept_v2.9.dat .
CARD=${CARD:-$PHOKHARA_CARD}   # submit.sh CARD=<template> overrides the production card
sed "s/@SEED@/$SEED/;s/@NEVENTS@/$NEVENTS/;s/@NMAX@/$NMAX/" "$CARD" > input.dat
start=$(date +%s)
"${EXE:-$PHOKHARA_EXE}" input.dat > phokhara.out 2>&1   # submit.sh EXE=<binary> runs a variant
echo "exit=$? seconds=$(( $(date +%s) - start )) host=$(hostname)" > done.txt
rm -f vpol_*.dat const_and_model_paramall10.0.dat
