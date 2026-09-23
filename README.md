# CEEX_PHOKHARA_ANALYSIS

**Result: [REPORT/report.pdf](REPORT/report.pdf).** The discrepancy is two errors in PHOKHARA's
1-photon ISR x FSR interference at NLO; with the fix (RUN/RUN_PHOKHARA/variants/h1.patch + h3.patch)
PHOKHARA agrees with CEEX and BabaYaga.

CEEX vs PHOKHARA for one scenario only: **KLOE-LA (KLOE-I), e⁺e⁻ → π⁺π⁻γ,
fixed-order NLO, F(π) = 1, no vacuum polarisation.** `RUN/` makes and merges
the data for both generators, `PLOTS/` plots it, `RESULTS/` holds the plots.
Everything is organised by a **run name** (`test10k`, `prod100k`, ...).

**The problem.** The total cross sections agree, 0.26839 nb for every generator.
The pion polar angles `lth+`, `lth-` and `lthav` do not. CEEX/Phokhara runs from
0.95 at θ⁺ = 50° to 1.20 at 130°, and θ⁻ is the mirror image. Every other
observable agrees. In the data from before this folder existed, CEEX and
BabaYaga agree bin by bin to about 0.02%, and Phokhara is the one that differs.
For θ⁺ the forward-backward asymmetry is 0.2373 in CEEX, 0.2372 in BabaYaga
and 0.2786 in Phokhara. It is not a mislabelled charge or beam direction: all
three generators pass the C-mirror test θ⁺(θ) = θ⁻(180°−θ).

| | |
|---|---|
| CEEX | `~/software/CEEX-main`, a worktree of `main` (e05d007). `pipig --NLO` with GoSam `eepipig_noVP_1L_onshell` + `eepipigg`, run from the frozen binary `MC_mpi` |
| Phokhara | PHOKHARA 10.0 snapshot in `RUN/RUN_PHOKHARA/src/` (from `~/software/PHOKARA_10.0` @ 133d68b, see `SOURCE_PROVENANCE.txt`), built with the KLOE-I cuts `variables_cuts_KLOE-I.f`. Card `RUN/RUN_PHOKHARA/cards/input_KLOE-LA_pipi_NLO_noVP_FF1.template.dat`: nlo = nlo2 = 1, IFSNLO = 1, ISR+INT+FSR, ivac = 0, FF_pion = −1, GVMD = 0, no f0, w = 1e-5, 18 histograms × 600 bins |
| BabaYaga | `PLOTS/DATA/babayaga/`, copied from `CEEX_ANALYSIS/PLOTS/DATA/data_kloe_la_bb_pi/BB_*.txt` |
| old Phokhara reference | `PLOTS/DATA/phokhara_ref/`, copied from `CEEX_ANALYSIS/PLOTS/DATA/data_kloe_la_bb_pi/Phokhara/` (5 Aug). Its `NLOnovp_*` files are the muon result, not pions |

The PHOKHARA source tree is not in git (250 MB with prebuilt libraries). The repo
keeps what differs from `PHOKARA_10.0` @ 133d68b: `variables_cuts_KLOE-I.f`,
`phokhara_nostop.patch`, and the rebuild recipe in `SOURCE_PROVENANCE.txt`.
`phokhara_nostop`, the binary the jobs use, comments out the three
`if (Mmax(i).lt.inte) stop` lines: only weighted histograms are used, and the
maximum only steers the channel split and the unweighting.

## Layout

```
RUN/config.sh                        every path; sourced by every script
RUN/RUN_CEEX/submit.sh               ./submit.sh <run> <n_seeds> <n> [walltime] [ecuts]
RUN/RUN_CEEX/run_ceex.sh             SLURM array task: one (seed, Emin), 5 MPI ranks, --n per rank
                                     (SLURM logs: ~/scratch/CEEX_PHOKHARA_ANALYSIS/slurm-out/, not home -- the home file quota filled up on 23 Sep)
RUN/RUN_PHOKHARA/submit.sh           ./submit.sh <run> <n_seeds> <nges> <nm> [walltime] [seed_offset]
RUN/RUN_PHOKHARA/run_phokhara.sh     SLURM array task: one seed
RUN/RUN_PHOKHARA/cards/              runcard template (+ README: where each switch comes from)
RUN/RUN_PHOKHARA/src/                PHOKHARA source + built binary `phokhara`
RUN/POST_PROCESS/post_process.sh     ./post_process.sh <run> [ceex|phokhara|all] -> PLOTS/DATA/<run>/
RUN/POST_PROCESS/check_total.sh      ./check_total.sh -l <scratch run dir>: flag CEEX outputs >5 robust sigma off, or error >10x median
RUN/POST_PROCESS/quarantine.sh       ./quarantine.sh <run>: move the outputs check_total.sh flags to <run>_excluded/ (reversible, logged)
RUN/POST_PROCESS/snapshot.sh         ./snapshot.sh <src_run> <dst_run>: link the finished part of a running run under a new name
RUN/POST_PROCESS/merge.py, average.py  CEEX merge (unmodified copies from CEEX_ANALYSIS)
RUN/POST_PROCESS/merge_phokhara.py   Phokhara seed_*/NLOFF1.dat -> NLOFF1_<obs>.csv + sigma.txt
PLOTS/Makefile                       make plot RUN=<run> [UPDATE=1] [PREVIEW=1] [PHOK=...] [ECUTS=4,5] [TAR=1]
PLOTS/PLOTTING_SCRIPTS/plot_compare.py
PLOTS/DATA/<run>/{ceex,phokhara}/    merged data of one run
PLOTS/DATA/<run>/{babayaga,phokhara_ref} -> ../babayaga, ../phokhara_ref (shared references)
RESULTS/<run>/                       plots + summary.txt of one run
```

Raw output lives outside the tree, one directory per run:

```
~/scratch/CEEX_PHOKHARA_ANALYSIS/CEEX/<run>/RUN_CEEX_<seed>_<ecut>/output_<rank>.txt
~/scratch/CEEX_PHOKHARA_ANALYSIS/PHOKHARA/<run>/seed_<k>/{input.dat,phokhara.out,NLOFF1.dat,done.txt}
```

Both `submit.sh` refuse a run name that already exists, so a new submission can
never delete an old run's output.

## Run

```sh
cd RUN
RUN_CEEX/submit.sh     test10k 30 10k     00:30:00            # 60 tasks: 30 seeds x Emin {1e-4,1e-5}
RUN_PHOKHARA/submit.sh test10k 30 10000 10000   00:20:00      # 30 seeds, nges=10k, nm=10k
```

Never relink `CEEX_EXE` while an array is running. To test a change, build a
new tagged binary (`make WITH_MPI=1 EXE=$PWD/MC_<tag>`) and set `CEEX_EXE` to it.
The Phokhara binary is rebuilt with

```sh
cd RUN/RUN_PHOKHARA/src
make phokhara ROOT_DIR=$PWD/eemmg-lib/ VARIABLES_CUTS_FILE=variables_cuts_KLOE-I.f
```

(`variables_cuts.f` of PHOKARA_10.0 is an empty stub: no cuts, no histograms.)

### Cost (Barkla `nodes`, measured 23 Sep)

| | per 1k events | "event" |
|---|---|---|
| CEEX | ~6-7 s per MPI rank | 1k of `--n`: 1k nph=1 + 16k nph=2 VEGAS points (auto nw = 1,1,16), adaptation and production |
| Phokhara | ~0.9-1.25 s | one weighted event passing the cuts (~16 trial points) |

Phokhara's `nm` (weight-maximum scan) and `nges` (production) both count
events passing the cuts, at the same cost, and the scan runs first. Nothing
from the scan reaches the histograms. Unpatched PHOKHARA **stops** if a weight
exceeds the scanned maximum ("Max(i) too small!") and writes no histograms,
which forced a long scan (nm = 2M: 35-45 min per seed; Strong2020 used 20M).
`phokhara_nostop` only warns, so nm = 10k (~10 s) is enough and a seed costs
about nges x 1 ms. Fortran buffers stdout, so `phokhara.out` only fills at the end. CEEX runs below ~100k events per rank
undershoot (see the CEEX README), so low-stat CEEX numbers test the pipeline,
not the physics.

## Merge and plot

CEEX first: screen for diverged rank outputs, and take them out (reversibly)
before merging -- `average.py` already drops them from sigma, but `merge.py`
would put them in the histograms:

```sh
cd RUN/POST_PROCESS
./check_total.sh -l ~/scratch/CEEX_PHOKHARA_ANALYSIS/CEEX/<run>   # list only (also run by post_process.sh)
./quarantine.sh <run>                                             # move flagged outputs to <run>_excluded/
```


```sh
cd PLOTS
source source.sh                         # plots conda env
make runs                                # which runs have merged data
make plot RUN=test10k UPDATE=1           # re-merge the run's CEEX + Phokhara into DATA/test10k, then plot
make plot RUN=test10k PHOK=phokhara_ref  # use the old Phokhara set as the denominator
make plot RUN=test10k ECUTS=5 PREVIEW=1  # one Emin, terminal previews of the angle plots
```

Any source can be missing. The script reports it and plots whatever is there,
so the new and old Phokhara sets can be compared before CEEX is finished.
Without CEEX, panel 1 and the BabaYaga table show **Phokhara / BabaYaga**
(new and old Phokhara sets) instead of CEEX / BabaYaga.

Output in `RESULTS/<run>/`, at 600, 60 and 10 bins:

- `pi_kloe_la_<obs>.pdf` has the distribution and two ratio panels:
  1. **CEEX / BabaYaga**: CEEX against the independent NLO code it agrees with.
  2. **{CEEX, BabaYaga} / Phokhara**: both against Phokhara, where the tilt
     shows.

  Each numerator carries its own MC error. The denominator's error is the band
  around 1, drawn in its colour. The old Phokhara set appears only in the
  distribution panel.
- `overview_vs_babayaga.pdf` shows panel 1 for every observable on one page, and
  `overview_vs_phokhara.pdf` does the same for panel 2.
- `summary.txt` has five tables:
  - σ per source for each observable;
  - shape χ²/ndf against Phokhara;
  - shape χ²/ndf of CEEX against BabaYaga;
  - forward-backward asymmetries of θ± and θ_γ;
  - the C-mirror χ²/ndf, which must be about 1 for any generator.

`PHOK` picks the Phokhara set: `phokhara` (the run's own, the default) or
`phokhara_ref` (the old 5-Aug set, also used when the run has no Phokhara).

CEEX fills only the 14 observables in `SCRIPTS/ANALYSIS/Histo.f`. Phokhara's
`lmxxg`, `lmtrk`, `lmxxc` and `lmtrkc` are plotted against the other references
only. CEEX's `lmxx` is Phokhara's `lmmx`.

## Earlier runs kept

| run | what |
|---|---|
| `partial_1151_ceex100k_phok4x20k` | DATA + RESULTS only: a merge made at 11:51 of the CEEX 100k production while it was running, with the first 4 Phokhara timing seeds |
| `prod500k` | CEEX 30 seeds x Emin {1e-4,1e-5} x 500k x 5 ranks: 59/60 tasks (18_5 cancelled after 1h16, set aside unfinished), 1/295 outlier rank quarantined; Phokhara 300 seeds x 500k. sigma: CEEX 0.26840(4) / 0.26836(4), Phokhara 0.268353(46), BabaYaga 0.268389(4) nb. A(th+): CEEX 0.23751(13) / 0.23752(14), BabaYaga 0.23724(1), Phokhara 0.27872(16). Pion-angle shapes CEEX vs Phokhara chi2/ndf 1060-1560 |
| `prod500k_partial` | snapshot of `prod500k` at 14:11: CEEX 27/60 tasks (14 at Emin 1e-4, 15 at 1e-5, no outliers flagged), Phokhara 300/300. sigma: CEEX 0.26842(5) / 0.26834(6), Phokhara 0.26835(5), BabaYaga 0.268389(4) nb. A(th+): CEEX 0.2376(2) / 0.2378(2), BabaYaga 0.2372, Phokhara 0.2787(2) |
| `prod100k` | CEEX 30 seeds x Emin {1e-4,1e-5} x 100k x 5 ranks, 11/300 outlier ranks quarantined; Phokhara 30 seeds x 100k. sigma: CEEX 0.26833(19) / 0.26779(23), Phokhara 0.26867(32) nb. A(th+): CEEX 0.2381(7) / 0.2390(8), BabaYaga 0.2372, Phokhara 0.2764(11) |
| `test100k` | snapshot of `prod100k` at 12:49: CEEX 22/60 tasks (11 per Emin) x 100k x 5 ranks, 3 outlier ranks quarantined (107 outputs), Phokhara all 30 seeds x 100k (sigma_MC 0.26867(32) nb). A(th+): CEEX 0.2403(12) at Emin 1e-5, BabaYaga 0.2372, Phokhara 0.2764(11) |
| `test10k` | DATA + RESULTS: CEEX 30 seeds x Emin {1e-4,1e-5} x 10k x 5 ranks; Phokhara (`phokhara_nostop`) 30 seeds x nges 10k, nm 10k, ~11 s per seed. Pipeline check: Phokhara sigma_MC 0.26840(105) nb, A(th+) 0.278(4) as in the old reference |
| `test_ceex10k_phok20k` | DATA + RESULTS: CEEX 2 seeds x 10k, Phokhara 8 seeds x 20k (raw in scratch `CEEX/test_10k_2seeds`, `PHOKHARA/timing_20k`) |
| CEEX 100k production (cancelled 12:08, 59/60 tasks done) | raw only, still at `~/scratch/CEEX-main/KLOE-LA_NLO_pipig` (old layout, not merged) |
