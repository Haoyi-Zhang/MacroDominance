#!/usr/bin/env python3
"""Draw the analytic self-context slice with optional Matplotlib.

Run: python scripts/plot_figures.py [--font-file path/to/times.ttf]
Use Windows Times New Roman or an installed Times New Roman font. On systems
without it, Matplotlib's bundled STIXGeneral is a Times-like portable fallback;
--font-file selects the publisher-matching face. No font is redistributed.
Math uses the selected Times family with Unicode-correct Greek symbols. The original
three samples t=0,1,2 exactly describe both piecewise-linear functions. This
script runs no placement experiment. Native output: figures/dominance.pdf,
234 x 145 PDF points; identical bytes go to sibling paper/figures when present.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil

import matplotlib as mpl
mpl.use("Agg")
from matplotlib import font_manager as fm
from matplotlib import pyplot as plt

ROOT = Path(__file__).resolve().parents[1]


def configure_font(path: Path | None) -> str:
    if path is None:
        windows = Path(os.environ.get("WINDIR", "")) / "Fonts/times.ttf"
        if windows.is_file():
            path = windows
        else:
            try:
                path = Path(fm.findfont("Times New Roman", fallback_to_default=False))
            except ValueError:
                path = Path(mpl.get_data_path()) / "fonts/ttf/STIXGeneral.ttf"
    if not path.is_file():
        raise FileNotFoundError(path)
    fm.fontManager.addfont(str(path))
    family = fm.FontProperties(fname=str(path)).get_name()
    mpl.rcParams.update({
        "font.family": family, "font.size": 8, "mathtext.fontset": "custom",
        "mathtext.rm": family, "mathtext.it": f"{family}:italic",
        "mathtext.bf": f"{family}:bold", "mathtext.fallback": "stix",
        "pdf.fonttype": 42, "pdf.use14corefonts": False, "text.usetex": False,
        "axes.unicode_minus": False, "axes.linewidth": .5, "path.simplify": False,
    })
    return family


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font-file", type=Path)
    args = parser.parse_args()
    family = configure_font(args.font_file)
    t = [0, 1, 2]
    p = t
    q = [2 + abs(1 - value) for value in t]
    if [a - b for a, b in zip(p, q)] != [-3, -1, -1]:
        raise ArithmeticError("Self-context slice differs from the analytic example")
    fig = plt.figure(figsize=(234 / 72, 145 / 72))
    ax = fig.add_axes([28 / 234, 56 / 145, 201 / 234, 83 / 145])
    ax.plot(t, p, color="black", lw=.8, label=r"$P$: $\tau_P=0$, $[0,0]$")
    ax.plot(t, q, color="black", lw=.8, ls="--", label=r"$Q$: $\tau_Q=2$, $[1,1]$")
    ax.plot([1, 1], [1, 2], "o", ms=4, color="black")
    ax.annotate("", xy=(1, 1.95), xytext=(1, 1.05),
                arrowprops={"arrowstyle": "<->", "lw": .6, "color": "black",
                            "shrinkA": 0, "shrinkB": 0, "mutation_scale": 6})
    ax.text(.96, 1.5, r"$E(P,Q)=-1$", ha="right", va="center", fontsize=8)
    ax.set(xlim=(0, 2), ylim=(0, 3.4),
           xlabel=r"Exterior point $a=b=t$", ylabel="Adjusted response")
    ax.xaxis.label.set_size(9)
    ax.yaxis.label.set_size(9)
    ax.set_xticks([0, 1, 2])
    ax.set_yticks([0, 1, 2, 3])
    ax.tick_params(length=2, width=.5, pad=2)
    ax.grid(color=".80", lw=.35)
    ax.set_axisbelow(True)
    ax.legend(loc="upper center", bbox_to_anchor=(.5, -.37), frameon=False,
              fontsize=8, borderaxespad=0, handlelength=2)
    output = ROOT / "figures/dominance.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, metadata={"Creator": None, "Producer": None, "CreationDate": None, "ModDate": None})
    plt.close(fig)
    paper = ROOT.parent / "paper/figures"
    if paper.is_dir():
        shutil.copyfile(output, paper / output.name)
    print(f"dominance: t=0,1,2; P=t, Q=2+abs(1-t); E(P,Q)=-1 at t=1; embedded {family}")


if __name__ == "__main__":
    main()
