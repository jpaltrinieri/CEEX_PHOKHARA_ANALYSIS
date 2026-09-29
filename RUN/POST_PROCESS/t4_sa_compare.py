#!/usr/bin/env python3
"""T4 at KLOE small-angle kinematics: is the massless ISR one-loop amplitude of B5
(NLO_ISR_no_mass_terms) good enough when the photon is collinear to a beam?

Usage: t4_sa_compare.py <dir>
  <dir>/t4_points.txt        phokhara_dump_sa (dump.patch + sa_cuts.patch, unpatched physics)
  <dir>/t4_ceex*.txt         t4_ceex on the same points, one file per CEEX --thg_cutoff
                             (t4_ceex.txt = default 3 deg, t4_ceex_c1.txt, t4_ceex_c0.3.txt)

Per point: C-odd difference PHOKHARA - CEEX of the 1-photon NLO correction, minus the exact
H1 + H2 terms (as in T4), and the C-even difference; both divided by the C-even tree, binned in
the photon angle to the nearest beam. Below --thg_cutoff CEEX does not evaluate its virtual
correction directly but extrapolates D = a + b ln(2 p.k) from anchors at the cutoff and 3x it.
"""
import os, sys
import numpy as np

d = sys.argv[1]
P = np.loadtxt(f"{d}/t4_points.txt"); t = P[:, 26:46]; fac = t[:, 12]
ev = lambda x: (x[0::2] + x[1::2]) / 2; od = lambda x: (x[0::2] - x[1::2]) / 2
treeP = fac * t[:, 5]; tP = ev(treeP)
B3, B4, B5 = fac * t[:, 2], fac * t[:, 3], fac * t[:, 4]; verf, vers = t[:, 18], t[:, 19]
alpha = 1 / 137.035999084; me = 0.51099895e-3; s = 1.02**2; w = 9.8039215686e-6; L = np.log(me**2 / s)
soft = alpha / np.pi * (-np.log(4 * w * w) * (1 + L) - L**2 / 2 - L - np.pi**2 / 3)
h = od(B4 - B3 / 2 * (verf + vers) + B3 / 2 * (1 + soft)) / tP        # H1 + H2, exact per point
x3 = od(B3) / tP                                                        # tree interference / tree
b5 = od(B5 - B3 / 2 * (1 + soft)) / tP                                  # fixed B5 = massless 2Re[F* dI_e]
g = P[0::2, 10:14]; th = np.arccos(np.abs(g[:, 3]) / np.linalg.norm(g[:, 1:], axis=1))
bins = ((0, 1e-3), (1e-3, 5.2e-3), (5.2e-3, 1.75e-2), (1.75e-2, 5.24e-2), (5.24e-2, 4))
sel = [(th >= lo) & (th < hi) for lo, hi in bins]
cell = lambda X, k: f"{X[k].mean():+.1e}({X[k].std():.1e})".rjust(19)

out = [f"# T4-SA: {len(tP)} accepted 1-photon KLOE small-angle points (+ pi+<->pi- swaps), w*sqrt(s) = Emin = 1e-5 GeV",
       "# photon angle to the nearest beam [mrad]:  " + "  ".join(f"{lo*1e3:.1f}-{min(hi, .27)*1e3:.1f}" for lo, hi in bins),
       "points                  " + "".join(f"{k.sum():19d}" for k in sel),
       "|tree interference|/tree" + "".join(f"{np.mean(np.abs(x3[k])):19.1e}" for k in sel),
       "|B5 loop (fixed)|/tree  " + "".join(f"{np.mean(np.abs(b5[k])):19.1e}" for k in sel),
       "# residual per C-even tree, mean(rms) over points:"]
for f, lab in (("t4_ceex.txt", "3 deg"), ("t4_ceex_c1.txt", "1 deg"), ("t4_ceex_c0.3.txt", "0.3 deg")):
    if not os.path.exists(f"{d}/{f}"):
        continue
    C = np.loadtxt(f"{d}/{f}"); tC = ev(C[:, 1])
    R = od(P[:, 22:26].sum(1) - treeP) / tP - od(C[:, 6] - C[:, 1]) / tC - h
    E = ev(P[:, 22:26].sum(1) - treeP) / tP - ev(C[:, 6] - C[:, 1]) / tC
    out.append(f"C-odd - H1 - H2, {lab:7s}" + "".join(cell(R, k) for k in sel))
    out.append(f"C-even,          {lab:7s}" + "".join(cell(E, k) for k in sel))
txt = "\n".join(out); print(txt)
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "RESULTS", "t4_sa", "summary.txt"), "w").write(txt + "\n")
