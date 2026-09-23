# REPORT

`report.pdf` -- the full write-up. Rebuild:

```sh
~/.conda/envs/plots/bin/python3 make_numbers.py    # numbers.tex from the fix500k runs
~/.conda/envs/plots/bin/python3 make_figures.py    # figures/fig_{wscan,t3,t4}.pdf
module load apptainer/1.3.6
APPTAINER_BINDPATH=/mnt,/opt/apps apptainer run \
  /opt/apps/pkg/applications/containers/latex/2023/pdflatex_24.04.sif -interaction=nonstopmode report.tex   # twice
```

The site `pdflatex` wrapper (module texlive/2023) drops every argument after the first, so the
container is called directly. The remaining figures come from `../RESULTS/{prod500k,final500k}`.
