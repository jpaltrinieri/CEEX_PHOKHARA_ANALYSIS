#!/usr/bin/env python3
"""T4: point-by-point comparison of the 1-photon NLO matrix element (Born + virtual + soft
below the cutoff), CEEX vs PHOKHARA, split into C-even and C-odd parts by the pi+<->pi- swap.

Usage: t4_compare.py <dir>     with <dir>/t4_points.txt (PHOKHARA phokhara_dump) and
                               <dir>/t4_ceex.txt (RUN_CEEX/t4/t4_ceex on the same points)

Rows come in pairs (iswap=0: the event, iswap=1: pi+ and pi- momenta exchanged). For any
quantity X:  X_even = (X0+X1)/2,  X_odd = (X0-X1)/2. Everything is divided by the code's own
C-even tree at that point, so no overall normalisation enters.

PHOKHARA pieces (all in the units of helicityampLO, fac = t4v(13)):
  A    = amplit                 ISR |I|^2 with ISR virtual (C-even)
  B1   = |F|^2 (1+ver_s)        B2 = |I|^2 ver_f          (C-even)
  B3   = 2 Re[I* F]             tree interference (C-odd)
  B4   = Re[T1+T2+T3] + Re[T4 (ver_f+ver_s)]   as coded (H1)
  B5   = Re[F* (apl-ami)]       ISR one-loop x FSR tree (H2 sits here)
  S    = NLOpions = tree x 2 (pjpj - p1p2 + qjqj - q1q2 + IF)   soft eikonals
  V    = virt_pions = pFSR + pISR + vFSR (+ GVMD = 0)             loops
CEEX:  amp2 = tree (1 + aD + act - YFSv + YFS).
"""
import sys
import numpy as np

d = sys.argv[1]
P = np.loadtxt(f"{d}/t4_points.txt")
C = np.loadtxt(f"{d}/t4_ceex.txt")
assert len(P) == len(C) and np.all(P[:, 0] == C[:, 0]) and np.all(P[0::2, 0] == 0) and np.all(P[1::2, 0] == 1)
t = P[:, 26:46]; fac = t[:, 12]
p = {
    "A": P[:, 22], "B1": fac * t[:, 0], "B2": fac * t[:, 1], "B3": fac * t[:, 2], "B4": fac * t[:, 3],
    "B5": fac * t[:, 4], "S": P[:, 24], "V": P[:, 25],
    "pFSR": t[:, 13], "pISR": t[:, 14], "vFSR": t[:, 15],
}
p["tree"] = fac * t[:, 5]
p["tot"] = P[:, 22] + P[:, 23] + P[:, 24] + P[:, 25]
# soft split: S = tree * 2 * (soft sum); the C-odd soft integral is the initial-final one
soft = {"ISR": t[:, 8] - t[:, 7], "FSR": t[:, 10] - t[:, 9], "IF": t[:, 11]}
for k, v in soft.items():
    p["S_" + k] = p["tree"] * 2 * v
c = {"tree": C[:, 1], "tot": C[:, 6]}
for i, k in enumerate(("aD", "act", "YFSv", "YFS"), 2):
    c[k] = C[:, i]

ev = lambda x: (x[0::2] + x[1::2]) / 2
od = lambda x: (x[0::2] - x[1::2]) / 2
n = len(P) // 2
tP, tC = ev(p["tree"]), ev(c["tree"])

print(f"{n} points (+ swaps) from {d}\n")
r = c["tree"] / p["tree"]
print(f"tree normalisation CEEX/PHOKHARA: mean {r.mean():.8f}  rel. spread {r.std()/r.mean():.2e}")
print(f"tree C-odd/C-even:   CEEX mean {np.mean(od(c['tree'])/tC):+.6f}   PHOKHARA mean {np.mean(od(p['tree'])/tP):+.6f}"
      f"   max |diff| {np.max(np.abs(od(c['tree'])/tC - od(p['tree'])/tP)):.2e}\n")

def line(name, xC, xP):
    a, b = xC, xP; dlt = b - a
    print(f"  {name:28s} CEEX {a.mean():+.5f} (rms {a.std():.4f})   PHOKHARA {b.mean():+.5f} (rms {b.std():.4f})"
          f"   P-C mean {dlt.mean():+.5f}  rms {dlt.std():.5f}")

print("NLO correction (total - tree), per point, / C-even tree:")
line("C-even", ev(c["tot"] - c["tree"]) / tC, ev(p["tot"] - p["tree"]) / tP)
line("C-odd", od(c["tot"] - c["tree"]) / tC, od(p["tot"] - p["tree"]) / tP)

print("\nPHOKHARA C-odd pieces / C-even tree (mean over points):")
for k in ("A", "B1", "B2", "B3", "B4", "B5", "S_ISR", "S_FSR", "S_IF", "pISR", "pFSR", "vFSR"):
    print(f"  {k:6s} {np.mean(od(p[k]) / tP):+.5f}   (C-even {np.mean(ev(p[k]) / tP):+.5f})")
print("  B3/2 (=Re[I*F], the tree interference once):", f"{np.mean(od(p['B3']) / tP) / 2:+.5f}")
print("\nCEEX C-odd pieces / C-even tree (tree x factor, mean over points):")
for k in ("aD", "act", "YFSv", "YFS"):
    x = c["tree"] * c[k] * (-1 if k == "YFSv" else 1)
    print(f"  tree*{k:5s} {np.mean(od(x) / tC):+.5f}   (C-even {np.mean(ev(x) / tC):+.5f})"
          f"    factor itself: odd {np.mean(od(c[k])):+.5f} even {np.mean(ev(c[k])):+.5f}")
