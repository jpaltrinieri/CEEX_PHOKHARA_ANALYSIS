# CEEX vs Phokhara, KLOE-LA pi+pi-gamma, fixed-order NLO, F(pi)=1, no VP.
#
#   source source.sh                   once per shell (plots conda env)
#   make plot RUN=<run> [UPDATE=1] [PREVIEW=1] [PHOK=phokhara_ref] [ECUTS=4,5] [TAR=1]
#   make clean RUN=<run>
#   make runs                          list the runs that have merged data
#
# RUN names one run: DATA/<run>/ -> ../RESULTS/<run>/. UPDATE=1 first reruns
# ../RUN/POST_PROCESS/post_process.sh <run>, i.e. re-merges that run's CEEX and
# Phokhara scratch trees into DATA/<run>/ (paths in ../RUN/config.sh).
# Ratio panels: CEEX / BabaYaga, and {CEEX, BabaYaga} / Phokhara. PHOK picks
# the Phokhara set: phokhara (this run, default) or phokhara_ref (old 5-Aug set).

PYTHON  ?= $(or $(CONDA_PREFIX),$(HOME)/.conda/envs/plots)/bin/python3
DATA    := DATA
RESULTS := ../RESULTS
SCRIPT  := PLOTTING_SCRIPTS/plot_compare.py

RUN     ?=
UPDATE  ?= 0
PREVIEW ?= 0
TAR     ?= 0
PHOK    ?=
ECUTS   ?=

FLAGS := $(if $(filter 1,$(PREVIEW)),,--no-preview) \
         $(if $(PHOK),--phokhara=$(PHOK)) $(if $(ECUTS),--ecuts=$(ECUTS))

.PHONY: plot update clean runs check-run

check-run:
	@if [ -z "$(RUN)" ]; then echo "set RUN=<run>; available:"; ls $(DATA) | grep -v -x -e babayaga -e phokhara_ref; exit 1; fi

runs:
	@ls $(DATA) | grep -v -x -e babayaga -e phokhara_ref

update: check-run
	../RUN/POST_PROCESS/post_process.sh $(RUN) all

plot: check-run $(if $(filter 1,$(UPDATE)),update)
	$(PYTHON) $(SCRIPT) $(DATA)/$(RUN) $(RESULTS)/$(RUN) $(FLAGS)
	@if [ "$(TAR)" = 1 ]; then tar -C $(RESULTS) -czf $(RESULTS)/$(RUN).tar.gz $(RUN) && echo "tar -> $(RESULTS)/$(RUN).tar.gz"; fi

clean: check-run
	rm -rf $(RESULTS)/$(RUN) $(RESULTS)/$(RUN).tar.gz
