#!/bin/bash
# Source this file (do not execute it) to set up the environment needed to
# run the plotting scripts in this directory:
#
#   source source.sh
#
# It loads the miniforge3 module and activates the "plots" conda env, which
# provides matplotlib, Pillow and numpy for plot_histos.py and everything
# under PLOTTING_SCRIPTS/.

if [ -z "${LMOD_CMD:-}" ]; then
    source /etc/profile.d/modules.sh
fi

module load miniforge3/25.3.0-python3.12.10

CONDA_BASE="$(conda info --base)"
source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate plots

echo "Environment ready: $(python3 --version) from $(which python3)"
