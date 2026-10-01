"""Render one publication figure from result JSONs (no computation beyond plotting).

  --fig power      --power analysis/outputs/power.json
  --fig fairness   --fairness analysis/outputs/fairness.json --descriptive analysis/outputs/descriptive.json
  --fig holds      --fp analysis/outputs/fp_models.json --descriptive analysis/outputs/descriptive.json
  --fig rt_hist    --descriptive analysis/outputs/descriptive.json
  --fig terciles   --fp analysis/outputs/fp_models.json
  --fig policies   --fairness analysis/outputs/fairness.json

Writes the PNG to --out and a PDF next to it (deterministic metadata).
Usage: .venv\\Scripts\\python.exe analysis\\make_figures.py --fig holds --fp ... --descriptive ... --out analysis/figures/holds.png
"""
from __future__ import annotations

import _env  # noqa: F401

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from common import AXIS, GRID, INK, INK2, MUTED, PAL, SERIES, save_fig, set_style

# championships with official holds; five series in a scatter need marker shape as the
# secondary identity channel (the palette validates only three colours all-pairs)
COMP_COLOR = {"WCH2022": PAL["blue"], "WCH2023": PAL["orange"], "WCH2025": PAL["aqua"],
              "WIC2024": PAL["yellow"], "WIC2025": PAL["magenta"]}
COMP_MARK = {"WCH2022": "o", "WCH2023": "s", "WCH2025": "^", "WIC2024": "D", "WIC2025": "v"}


def load(p):
    d = json.loads(Path(p).read_text(encoding="utf-8"))
    return d


def T(d, name):
    return pd.DataFrame(d["tables"][name])


def _mock(*ds):
    return any(x.get("mock") for x in ds if x)


# --------------------------------------------------------------------------------------------

def fig_power(args):
    import matplotlib.pyplot as plt
    from matplotlib.ticker import NullFormatter
    d = load(args.power)
    fine, mde = T(d, "curves_fine"), T(d, "mde")
    r = d["extra"]["r"]
    icc_obs = [i for i in d["extra"]["icc_grid"] if i not in (0.0, 0.05, 0.10, 0.20)]
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.9), gridspec_kw={"width_ratios": [1.3, 1]})
    ax = axes[0]
    marks = ["o", "s", "^", "D"]
    for c, m, icc in zip(SERIES, marks, (0.0, 0.05, 0.10, 0.20)):
        s = fine[fine["icc"] == icc]
        ax.plot(s["n_races"], s["power"], color=c, lw=1.6, label=f"{icc:.2f}", marker=m, markevery=12, ms=4)
    for icc in icc_obs:
        s = fine[fine["icc"] == icc]
        ax.plot(s["n_races"], s["power"], color=INK2, lw=1.4, ls=(0, (1, 1.2)), label=f"{icc:.3f} (observed)")
    ax.axhline(0.8, color=MUTED, lw=0.8)
    ax.set_xscale("log")
    ax.set_xticks([10, 20, 50, 100, 200, 400])
    ax.set_xticklabels(["10", "20", "50", "100", "200", "400"])
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xlim(8, 420)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Races with a measured hold (8 athletes each)")
    ax.set_ylabel("Power (two-sided, alpha 0.05)")
    ax.set_title(f"A  Detecting |r| = {r:.2f} (Haugen et al. 2013)", loc="left")
    ax.legend(loc="lower right", title="Residual race ICC", title_fontsize=7)
    ax = axes[1]
    for c, m, icc in zip(SERIES, marks, (0.0, 0.10, 0.20)):
        s = mde[mde["icc"] == icc]
        ax.plot(s["n_races"], s["mde_r_80"], color=c, lw=1.6, marker=m, ms=4, label=f"ICC {icc:.2f}")
    ax.axhline(r, color=MUTED, lw=0.8)
    ax.set_xscale("log")
    ax.set_xticks([20, 50, 100, 200, 400])
    ax.set_xticklabels(["20", "50", "100", "200", "400"])
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xlabel("Races")
    ax.set_ylabel("Minimum detectable |r| (80% power)")
    ax.set_title("B  Detectable effect by sample size", loc="left")
    ax.legend(loc="upper right")
    fig.tight_layout()
    save_fig(fig, args.out, _mock(d))


def fig_fairness(args):
    """Abstract candidate: hold vs championship calibration as drivers of legitimate FS risk."""
    import matplotlib.pyplot as plt
    f = load(args.fairness)
    desc = load(args.descriptive)
    sex = args.sex
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.5), gridspec_kw={"width_ratios": [1.15, 1]})
    ax = axes[0]
    if "cal_curves" in f["tables"]:
        cc = T(f, "cal_curves")
        cc = cc[cc["sex"] == sex]
        lo = cc[cc["slope_label"] == "measured_ci_low"].sort_values("hold_s")
        hi = cc[cc["slope_label"] == "measured_ci_high"].sort_values("hold_s")
        pt = cc[cc["slope_label"] == "measured_point"].sort_values("hold_s")
        plo, phi_ = lo["p"].to_numpy(), hi["p"].to_numpy()
        ax.fill_between(lo["hold_s"].to_numpy(), 1000 * np.minimum(plo, phi_), 1000 * np.maximum(plo, phi_),
                        color=MUTED, alpha=0.25, lw=0, label="measured slope, 95% CI")
        ax.plot(pt["hold_s"], 1000 * pt["p"], color=INK, lw=1.6, label="measured slope (Ready Time)")
        for sc, col, lab, mk in (("haugen_slower", PAL["orange"], "|r| = 0.16, slower when longer", "s"),
                                 ("haugen_faster", PAL["blue"], "|r| = 0.16, faster when longer", "o")):
            s = cc[cc["slope_label"] == sc].sort_values("hold_s")
            ax.plot(s["hold_s"], 1000 * s["p"], color=col, lw=1.6, marker=mk, markevery=16, ms=4, label=lab)
        holds = T(f, "measured_holds")["hold_s"].to_numpy()
        ymin, ymax = 1000 * cc["p"].min(), 1000 * cc["p"].max()
        rug_y = ymin / 6.0                      # rug strip sits below every curve
        ax.plot(holds, np.full_like(holds, rug_y), "|", color=INK2, ms=7, mew=0.6)
        ax.set_ylim(rug_y / 2.5, ymax * 2.0)
        ax.set_xlabel(f"Seiko Ready Time (s); ticks: {len(holds)} races")
    ax.set_yscale("log")
    ax.set_ylabel("Legitimate starts scored < 0.100 s\nper 1,000 starts (simulation)")
    ax.set_title("A  Starter's hold (Seiko Ready Time)", loc="left")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, fontsize=6.5, frameon=False)
    ax = axes[1]
    mt = T(f, "meets")
    mt = mt[(mt["sex"] == sex) & (mt["family"] == "exgauss")].sort_values("offset_ms")
    fsr = T(desc, "false_starts")
    fsr = fsr[fsr["by"] == "comp_year"].set_index("level")
    y = np.arange(len(mt))
    ax.scatter(1000 * mt["p_median_hold"], y, color=PAL["blue"], s=22, zorder=3, marker="o",
               label="modelled legitimate", edgecolor="white", linewidth=0.8)
    rec = mt["comp_year"].map(fsr["per_1000"])
    has = rec > 0
    ax.scatter(rec[has], y[has.to_numpy()], facecolor="white", edgecolor=PAL["orange"], s=24, zorder=3,
               marker="D", linewidth=1.1, label="recorded false starts (all causes)")
    ax.set_yticks(y)
    ax.set_yticklabels([f"{c}  ({o:+.0f} ms)" for c, o in zip(mt["comp_year"], mt["offset_ms"])], fontsize=6.5)
    ax.set_xscale("log")
    ax.set_xlabel("Per 1,000 starts (no hold effect)")
    ax.set_title("B  Championship RT offset", loc="left")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, fontsize=6.5, frameon=False)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    save_fig(fig, args.out, _mock(f, desc))


def fig_holds(args):
    """Abstract candidate: official holds vs RT within championships, and championship offsets."""
    import matplotlib.pyplot as plt
    fp = load(args.fp)
    desc = load(args.descriptive)
    rr = T(fp, "race_resid")
    nums = fp["numbers"]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.6), gridspec_kw={"width_ratios": [1.2, 1]})
    ax = axes[0]
    for cy in sorted(rr["comp_year"].unique()):
        s = rr[rr["comp_year"] == cy]
        # centre each championship's residual race means (championship fixed effect)
        ax.scatter(s["fp"], s["resid_ms"] - s["resid_ms"].mean(), s=10 + 1.2 * s["n"], alpha=0.85,
                   color=COMP_COLOR.get(cy, MUTED), marker=COMP_MARK.get(cy, "o"), edgecolor="white",
                   linewidth=0.6, label=cy)
    x = np.linspace(rr["fp"].min(), rr["fp"].max(), 50)
    xc = x - rr["fp"].mean()
    b, lo, hi = nums["slope_ms_per_100ms"]["value"], *nums["slope_ms_per_100ms"]["ci95"]
    ax.fill_between(x, np.minimum(lo * xc * 10, hi * xc * 10), np.maximum(lo * xc * 10, hi * xc * 10),
                    color=MUTED, alpha=0.25, lw=0)
    ax.plot(x, b * xc * 10, color=INK, lw=1.6, label="linear fit (95% CI)")
    if "spline_curve" in fp["tables"]:
        sc = T(fp, "spline_curve")
        # centre the spline effect on the race-weighted mean hold so it shares the points' zero
        w_eff = np.interp(rr["fp"], sc["fp"], sc["effect_ms"])
        ax.plot(sc["fp"], sc["effect_ms"] - np.average(w_eff, weights=rr["n"]), color=PAL["violet"], lw=1.4,
                label="spline (df 3)")
    hs = nums["haugen_slope_same_scale"]["value"]
    for sgn in (1, -1):
        ax.plot(x, sgn * hs * xc * 10, color=MUTED, lw=1.0, ls=(0, (4, 2)))
    ax.text(x[-1], hs * xc[-1] * 10, " |r|=0.16", color=MUTED, fontsize=6.5, va="center")
    ax.set_xlabel("Seiko Ready Time (s)")
    ax.set_ylabel("Race mean RT, adjusted (ms)")
    ax.set_title(f"A  Seiko Ready Time vs RT ({len(rr)} races)", loc="left")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3, fontsize=6.5, markerscale=0.8, frameon=False)
    ax = axes[1]
    me = T(desc, "meet_effects").sort_values("comp_year")
    y = np.arange(len(me))[::-1]
    colors = [PAL["green"] if c.startswith("OG") else PAL["violet"] for c in me["comp_year"]]
    ax.errorbar(me["deviation_ms"], y, xerr=[me["deviation_ms"] - me["lo"], me["hi"] - me["deviation_ms"]],
                fmt="none", ecolor=AXIS, elinewidth=1.0)
    for c, mk, lab in ((PAL["violet"], "o", "Worlds (Seiko)"), (PAL["green"], "s", "Olympics (Omega)")):
        sel = np.array([(col == c) for col in colors])
        ax.scatter(me["deviation_ms"][sel], y[sel], color=c, marker=mk, s=20, zorder=3, label=lab,
                   edgecolor="white", linewidth=0.6)
    ax.axvline(0, color=AXIS, lw=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(me["comp_year"], fontsize=6.5)
    ax.set_xlabel("Championship RT offset (ms, adjusted)")
    yr = f"{desc['numbers']['year_min']['value']}-{desc['numbers']['year_max']['value']}"
    ax.set_title(f"B  Championship RT offsets, {yr}", loc="left")
    ax.legend(loc="upper right", fontsize=6.5)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    save_fig(fig, args.out, _mock(fp, desc))


def fig_story(args):
    """Abstract figure: the starter's hold and the championship on one RT scale.

    Top: RT shift across the 10th-90th percentile Ready Time implied by the within-championship slope (95% CI),
    and the shift a Haugen-sized slope (|r| = 0.16) would imply. Bottom: athlete-adjusted championship offsets
    (95% CI). Everything is read from the result JSONs; the only computation is slope x percentile range."""
    import matplotlib.pyplot as plt
    fp = load(args.fp)
    desc = load(args.descriptive)
    rr = T(fp, "race_resid")
    nums = fp["numbers"]
    p10, p90 = np.percentile(rr["fp"].to_numpy(float), [10, 90])
    span = (p90 - p10) * 10                                   # Ready Time range in units of 100 ms
    b, lo, hi = nums["slope_ms_per_100ms"]["value"], *nums["slope_ms_per_100ms"]["ci95"]
    hs = nums["haugen_slope_same_scale"]["value"]
    me = T(desc, "meet_effects").sort_values("deviation_ms")
    n_c = len(me)

    fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(6.4, 4.4), sharex=True,
                                   gridspec_kw={"height_ratios": [1.1, max(3.0, n_c / 4.0)], "hspace": 0.32})
    # top: the hold
    y_meas, y_haug = 1.0, 0.0
    ax0.errorbar([b * span], [y_meas], xerr=[[b * span - lo * span], [hi * span - b * span]], fmt="o",
                 color=INK, ecolor=INK, elinewidth=1.6, capsize=3, ms=5, zorder=3)
    for sgn in (1, -1):
        ax0.scatter([sgn * hs * span], [y_haug], facecolor="white", edgecolor=PAL["orange"], s=30, marker="D",
                    linewidth=1.2, zorder=3)
    ax0.plot([-hs * span, hs * span], [y_haug, y_haug], color=PAL["orange"], lw=0.8, ls=(0, (3, 2)), zorder=2)
    ax0.set_yticks([y_meas, y_haug])
    ax0.set_yticklabels([f"Measured ({len(rr)} races)", "Haugen-sized (|r| = 0.16)"], fontsize=7)
    ax0.set_ylim(-0.7, 1.7)
    ax0.set_title("A  Starter's hold: RT shift from 10th to 90th percentile Ready Time", loc="left", fontsize=8)
    ax0.grid(axis="y", visible=False)
    ax0.axvline(0, color=AXIS, lw=0.8)
    # bottom: championships
    y = np.arange(n_c)
    colors = [PAL["green"] if c.startswith("OG") else PAL["violet"] for c in me["comp_year"]]
    ax1.errorbar(me["deviation_ms"], y, xerr=[me["deviation_ms"] - me["lo"], me["hi"] - me["deviation_ms"]],
                 fmt="none", ecolor=AXIS, elinewidth=1.0)
    for c, mk, lab in ((PAL["violet"], "o", "World Championships (Seiko)"), (PAL["green"], "s", "Olympics (Omega)")):
        sel = np.array([(col == c) for col in colors])
        ax1.scatter(me["deviation_ms"][sel], y[sel], color=c, marker=mk, s=18, zorder=3, label=lab,
                    edgecolor="white", linewidth=0.6)
    ax1.axvline(0, color=AXIS, lw=0.8)
    ax1.set_yticks(y)
    ax1.set_yticklabels(me["comp_year"], fontsize=6)
    yr = f"{desc['numbers']['year_min']['value']}-{desc['numbers']['year_max']['value']}"
    ax1.set_title(f"B  Championship: athlete-adjusted RT offsets, {n_c} championships {yr}", loc="left", fontsize=8)
    ax1.set_xlabel("RT shift (ms); bars are 95% CIs")
    ax1.legend(loc="lower right", fontsize=6.5, frameon=False)
    ax1.grid(axis="y", visible=False)
    fig.subplots_adjust(left=0.2, right=0.98, top=0.93, bottom=0.11)
    save_fig(fig, args.out, _mock(fp, desc))


def fig_story_wide(args):
    """Abstract figure, page-width layout: the starter's hold and the championship on one shared RT axis.

    Left: RT shift across the 10th-90th percentile Ready Time implied by the within-championship slope (95% CI) and
    by a Haugen-sized slope (|r| = 0.16). Right: athlete-adjusted championship offsets (95% CI), sorted.
    Same computation as fig_story; only the layout differs."""
    import matplotlib.pyplot as plt
    fp = load(args.fp)
    desc = load(args.descriptive)
    rr = T(fp, "race_resid")
    nums = fp["numbers"]
    p10, p90 = np.percentile(rr["fp"].to_numpy(float), [10, 90])
    span = (p90 - p10) * 10
    b, lo, hi = nums["slope_ms_per_100ms"]["value"], *nums["slope_ms_per_100ms"]["ci95"]
    hs = nums["haugen_slope_same_scale"]["value"]
    me = T(desc, "meet_effects").sort_values("deviation_ms").reset_index(drop=True)
    n_c = len(me)
    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(7.0, 2.75), sharey=True,
                                   gridspec_kw={"width_ratios": [1.0, 4.2], "wspace": 0.06})
    ax0.errorbar([0], [b * span], yerr=[[b * span - lo * span], [hi * span - b * span]], fmt="o", color=INK,
                 ecolor=INK, elinewidth=1.6, capsize=3, ms=5, zorder=3)
    ax0.plot([1, 1], [-hs * span, hs * span], color=PAL["orange"], lw=0.9, ls=(0, (3, 2)), zorder=2)
    ax0.scatter([1, 1], [hs * span, -hs * span], facecolor="white", edgecolor=PAL["orange"], s=28, marker="D",
                linewidth=1.2, zorder=3)
    ax0.set_xticks([0, 1])
    ax0.set_xticklabels([f"Measured\n({len(rr)} races)", "Haugen-sized\n(|r| = 0.16)"], fontsize=6.3)
    ax0.set_xlim(-0.6, 1.6)
    ax0.axhline(0, color=AXIS, lw=0.8)
    ax0.set_ylabel("RT shift (ms)")
    ax0.set_title("A  Starter's hold", loc="left", fontsize=8)
    ax0.grid(axis="x", visible=False)
    x = np.arange(n_c)
    is_og = me["comp_year"].str.startswith("OG").to_numpy()
    ax1.errorbar(x, me["deviation_ms"], yerr=[me["deviation_ms"] - me["lo"], me["hi"] - me["deviation_ms"]],
                 fmt="none", ecolor=AXIS, elinewidth=1.0)
    ax1.scatter(x[~is_og], me["deviation_ms"][~is_og], color=PAL["violet"], marker="o", s=16, zorder=3,
                edgecolor="white", linewidth=0.5, label="World Championships (Seiko)")
    ax1.scatter(x[is_og], me["deviation_ms"][is_og], color=PAL["green"], marker="s", s=16, zorder=3,
                edgecolor="white", linewidth=0.5, label="Olympics (Omega)")
    ax1.axhline(0, color=AXIS, lw=0.8)
    labels = [f"{c[:-4]}\n{c[-2:]}" for c in me["comp_year"]]      # 'WCH2022' -> 'WCH\n22'
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=5.6)
    ax1.set_xlim(-0.7, n_c - 0.3)
    yr = f"{desc['numbers']['year_min']['value']}-{desc['numbers']['year_max']['value']}"
    ax1.set_title(f"B  Championship (athlete-adjusted offsets, {n_c} championships, {yr})", loc="left", fontsize=8)
    ax1.legend(loc="upper left", fontsize=6.3, frameon=False)
    ax1.grid(axis="x", visible=False)
    fig.subplots_adjust(left=0.085, right=0.995, top=0.9, bottom=0.17)
    save_fig(fig, args.out, _mock(fp, desc))


# venue names for the end labels of the confound figure (codes from the data; unknown codes pass through)
VENUE = {"WCH1999": "Seville", "WCH2001": "Edmonton", "WCH2003": "Paris", "WCH2005": "Helsinki", "WCH2007": "Osaka",
         "WCH2009": "Berlin", "WCH2011": "Daegu", "WCH2013": "Moscow", "WCH2015": "Beijing", "WCH2017": "London",
         "WCH2019": "Doha", "WCH2022": "Eugene", "WCH2023": "Budapest", "WCH2025": "Tokyo", "OG2020": "Tokyo",
         "OG2024": "Paris", "WIC2024": "Glasgow", "WIC2025": "Nanjing"}


def _venue(code):
    """'WCH2022' -> 'Eugene 2022'."""
    return f"{VENUE[code]} {code[-4:]}" if code in VENUE else code


def _mute(colour, t=0.3):
    """A palette colour blended toward the muted grey by t (the compact confound figure's muted palette)."""
    from matplotlib.colors import to_hex, to_rgb
    return to_hex((1 - t) * np.array(to_rgb(colour)) + t * np.array(to_rgb(MUTED)))


def fig_confound(args):
    """Abstract figure for the confounder audit: page width, compact, 7.0 x 3.2 in, three panels in one row.

    A  Same races, two answers: the Seiko Ready Time-RT correlation in the same races, pooled over championships
       (Haugen-style) and centred within championship (race-cluster bootstrap 95% CIs; systematic.h1c_r_pooled and
       h1c_r_centred), with Haugen et al.'s r = 0.16.
    B  The limit moves with the championship: each championship's 1-in-1,000 barrier (men, ex-Gaussian, bootstrap
       95% CIs; systematic.json table h2_per_championship), sorted and coloured by whether it lies below the 0.100 s
       rule (checked against fig.barrier_below_rule); the band between the published proposals 0.094 s (Fiore et al.
       2025) and 0.115 s (Brosnan et al. 2017, men) shaded, its edges named; the bold 0.100 s rule; a bracket for
       the championship spread (systematic.h2_champ_barrier_range_ms_exgauss_M).
    C  Same rule, different odds: the modelled rate of legitimate starts wrongly disqualified per 1,000 at each
       championship under the current rule (guardband.json table championships, P0, with CIs; log axis), the uniform
       guard band (P1, hollow) and per-championship calibration (P2, flat line), with the guard band's cost in recorded
       false starts no longer flagged (guard.b_p1_n_unflagged of guard.b_n_fs_with_rt).
    B and C label only Eugene 2022 (ringed, one accent colour in both) and the championship at the other end.
    Segoe UI (DejaVu Sans if missing); exact size (no tight bbox); a one-line footnote states how B and C differ.
    Only literature constants are typed (0.16; 0.094, 0.100, 0.115 s); every other plotted or printed number comes
    from systematic.json, guardband.json or fig.json."""
    import matplotlib.pyplot as plt
    from matplotlib.ticker import LogLocator, NullLocator
    sj, gj, fj = load(args.systematic), load(args.guardband), load(args.fignums)
    n, gn, fn = sj["numbers"], gj["numbers"], fj["numbers"]
    haugen_r, fiore_ms, rule_ms, brosnan_ms = 0.16, 94.0, 100.0, 115.0
    blue, orange, aqua, accent = _mute(PAL["blue"]), _mute(PAL["orange"]), _mute(PAL["aqua"]), PAL["violet"]
    band = "#ecebe6"
    fs, fs_title = 6.2, 7.8
    W, H, bot, top = 7.0, 3.2, 0.50, 2.96
    rc = {"font.family": ["Segoe UI", "DejaVu Sans"], "savefig.bbox": "standard",
          "axes.grid": True, "axes.grid.axis": "y", "grid.color": "#efeee9", "grid.linewidth": 0.45,
          "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6, "xtick.major.size": 2.5,
          "ytick.major.size": 2.5, "xtick.labelsize": fs, "ytick.labelsize": fs, "xtick.labelcolor": INK2,
          "ytick.labelcolor": INK2, "axes.labelsize": 6.3, "axes.labelcolor": INK2, "axes.labelpad": 2.5,
          "axes.spines.top": False, "axes.spines.right": False, "legend.fontsize": 6.0}

    def end_labels(ax, codes):
        """Label only Eugene 2022 and the championship at the far end; the axis label carries the rest."""
        codes = list(codes)
        ie = codes.index("WCH2022") if "WCH2022" in codes else 0
        idx = sorted({ie, len(codes) - 1 if ie < len(codes) / 2 else 0})
        ax.set_xticks(idx)
        ax.set_xticklabels([_venue(codes[i]) for i in idx])
        ax.tick_params(axis="x", length=0, pad=2.5)
        for i, t_ in zip(idx, ax.get_xticklabels()):
            t_.set_ha("left" if i == 0 else "right" if i == len(codes) - 1 else "center")
            if codes[i] == "WCH2022":
                t_.set_color(accent)
                t_.set_fontweight("bold")

    with plt.rc_context(rc):
        fig = plt.figure(figsize=(W, H))
        panels = []                                          # (panel left edge, axes left, axes width), inches
        for p_left, a_left, a_w in ((0.06, 0.40, 1.24), (1.72, 2.09, 2.13), (4.36, 4.83, 2.12)):
            panels.append((fig.add_axes([a_left / W, bot / H, a_w / W, (top - bot) / H]), (a_left - p_left) / a_w))
        (ax0, t0), (ax1, t1), (ax2, t2) = panels

        # ---- A: same races, two answers ------------------------------------------------------------------
        rows = [("Pooled over\nchampionships", n["h1c_r_pooled"]), ("Within\nchampionship", n["h1c_r_centred"])]
        xa = np.array([0.0, 1.0])
        ax0.axhline(0, color=AXIS, lw=0.7, zorder=1)
        ax0.axhline(haugen_r, color=MUTED, lw=0.7, ls=(0, (3, 2)), zorder=1)
        ax0.text(1.47, haugen_r + 0.006, f"Haugen et al.\n2013: r = {haugen_r:.2f}", ha="right", va="bottom",
                 fontsize=fs, color=INK2, linespacing=1.1)
        for xi, (lab, e) in zip(xa, rows):
            est, (lo, hi) = e["value"], e["ci95"]
            ax0.errorbar([xi], [est], yerr=[[est - lo], [hi - est]], fmt="o", color=blue, ecolor=blue,
                         elinewidth=1.4, capsize=2.2, capthick=1.0, ms=4.5, mec="white", mew=0.7, zorder=3)
            ax0.text(xi - 0.1, est, f"{est:.2f}", ha="right", va="center", fontsize=6.4, color=INK)
        ax0.set_xticks(xa)
        ax0.set_xticklabels([r_[0] for r_ in rows], linespacing=1.1)
        ax0.tick_params(axis="x", length=0, pad=3)
        ax0.set_xlim(-0.5, 1.5)
        ax0.set_ylim(-0.08, 0.36)
        ax0.set_yticks([0, 0.1, 0.2, 0.3])
        ax0.set_ylabel("r, Seiko Ready Time vs RT (95% CI)")
        ax0.set_title("A  Same races, two answers", loc="left", x=-t0, fontsize=fs_title)

        # ---- B: the limit moves with the championship ------------------------------------------------------
        ch = pd.DataFrame(sj["tables"]["h2_per_championship"])
        ch = ch[(ch["sex"] == "M") & ch["eligible"].astype(bool)].sort_values(["barrier_ms_exgauss", "comp_year"])
        ch = ch.reset_index(drop=True)
        xb = np.arange(len(ch))
        b = ch["barrier_ms_exgauss"].to_numpy(float)
        blo, bhi = ch["barrier_exgauss_lo"].to_numpy(float), ch["barrier_exgauss_hi"].to_numpy(float)
        below = b < rule_ms
        assert int(below.sum()) == fn["barrier_below_rule"]["value"], "panel B colouring disagrees with fig.json"
        sp = n["h2_champ_barrier_range_ms_exgauss_M"]
        x_lo, x_hi = -1.7, len(ch) - 0.4
        ax1.axhspan(fiore_ms, brosnan_ms, color=band, lw=0, zorder=0)
        for yv in (fiore_ms, brosnan_ms):
            ax1.axhline(yv, color=MUTED, lw=0.7, ls=(0, (3, 2)), zorder=1)
        ax1.text(-0.6, brosnan_ms + 0.9, "0.115 s Brosnan et al. 2017", ha="left", va="bottom", fontsize=fs,
                 color=INK2)
        ax1.text(x_hi - 0.25, fiore_ms - 0.9, "0.094 s Fiore et al. 2025", ha="right", va="top", fontsize=fs,
                 color=INK2)
        ax1.axhline(rule_ms, color=INK, lw=1.4, zorder=1)
        ax1.text(x_hi - 0.25, rule_ms + 0.7, "0.100 s rule", ha="right", va="bottom", fontsize=fs, color=INK,
                 fontweight="bold")
        bx = -1.15                                           # bracket for the championship spread
        ax1.plot([bx, bx], [sp["min_ms"], sp["max_ms"]], color=INK, lw=0.9, zorder=3)
        for yv in (sp["min_ms"], sp["max_ms"]):
            ax1.plot([bx, bx + 0.35], [yv, yv], color=INK, lw=0.9, zorder=3)
        ax1.text(bx, sp["max_ms"] + 1.2, f"championships {sp['min_ms']:.0f}–{sp['max_ms']:.0f} ms", ha="left",
                 va="bottom", fontsize=fs, color=INK)
        ax1.errorbar(xb, b, yerr=[b - blo, bhi - b], fmt="none", ecolor=AXIS, elinewidth=0.9, zorder=2)
        ax1.scatter(xb[below], b[below], color=orange, s=15, zorder=3, edgecolor="white", linewidth=0.5,
                    label="below the rule")
        ax1.scatter(xb[~below], b[~below], color=blue, s=15, zorder=3, edgecolor="white", linewidth=0.5,
                    label="above the rule")
        i22 = np.flatnonzero((ch["comp_year"] == "WCH2022").to_numpy())
        if len(i22):
            ax1.scatter(xb[i22], b[i22], facecolor="none", edgecolor=accent, s=55, linewidth=1.1, zorder=4)
        end_labels(ax1, ch["comp_year"])
        ax1.set_xlim(x_lo, x_hi)
        ax1.set_ylim(np.floor(min(blo.min(), fiore_ms) - 3), np.ceil(max(bhi.max(), sp["max_ms"] + 6, brosnan_ms) + 1))
        ax1.set_ylabel("1-in-1,000 limit, men (ms)")
        ax1.set_xlabel(f"championships, sorted by limit (n = {len(ch)})")
        ax1.set_title("B  The limit moves with the championship", loc="left", x=-t1, fontsize=fs_title)
        ax1.legend(loc="lower right", frameon=False, handletextpad=0.2, borderaxespad=0.3, labelspacing=0.3)

        # ---- C: same rule, different odds -------------------------------------------------------------------
        gc = pd.DataFrame(gj["tables"]["championships"]).sort_values(["rate_p0", "comp_year"], ascending=[False, True])
        gc = gc.reset_index(drop=True)
        xc = np.arange(len(gc))
        r0, r0lo, r0hi = (gc[c].to_numpy(float) for c in ("rate_p0", "rate_p0_lo", "rate_p0_hi"))
        r1 = gc["rate_p1"].to_numpy(float)
        p2 = float(gc["rate_p2"].median())
        ax2.set_yscale("log")
        h_p2 = ax2.axhline(p2, color=aqua, lw=1.5, zorder=1, label="calibration: equal odds everywhere")
        ax2.errorbar(xc, r0, yerr=[r0 - r0lo, r0hi - r0], fmt="none", ecolor=AXIS, elinewidth=0.9, zorder=2)
        h_p0 = ax2.scatter(xc, r0, color=blue, s=15, zorder=3, edgecolor="white", linewidth=0.5,
                           label="current rule, 0.100 s (95% CI)")
        h_p1 = ax2.scatter(xc, r1, facecolor="white", edgecolor=blue, s=15, linewidth=0.9, zorder=3,
                           label=f"uniform guard band (g = {gn['g_ms']['value']:.0f} ms)")
        j22 = np.flatnonzero((gc["comp_year"] == "WCH2022").to_numpy())
        if len(j22):
            ax2.scatter(xc[j22], r0[j22], facecolor="none", edgecolor=accent, s=55, linewidth=1.1, zorder=4)
            un, nfs = gn["b_p1_n_unflagged"], gn["b_n_fs_with_rt"]["value"]
            bc = un.get("by_champ") or {}
            where = (f"all {VENUE.get(next(iter(bc)), next(iter(bc)))}" if len(bc) == 1 else
                     ", ".join(f"{VENUE.get(k_, k_)} {v_}" for k_, v_ in bc.items()))
            ax2.annotate(f"guard band cost: {un['value']} of {nfs} recorded\nfalse starts unflagged ({where})",
                         xy=(xc[j22][0], r1[j22][0]), xycoords="data", xytext=(0.03, 0.04), textcoords="axes fraction",
                         ha="left", va="bottom", fontsize=fs, color=INK, linespacing=1.1,
                         arrowprops=dict(arrowstyle="-|>", color=INK2, lw=0.7, shrinkA=1, shrinkB=3.5,
                                         mutation_scale=6, relpos=(0.04, 1.0)))
        end_labels(ax2, gc["comp_year"])
        ax2.set_xlim(-0.8, len(gc) - 0.4)
        ax2.set_ylim(10 ** (np.log10(min(r1.min(), r0lo.min())) - 0.35), 10 ** (np.log10(r0hi.max()) + 0.5))
        ax2.yaxis.set_major_locator(LogLocator(base=10, numticks=12))
        ax2.yaxis.set_minor_locator(NullLocator())
        ax2.set_ylabel("legitimate starts wrongly DQ'd\nper 1,000 (modelled, log)", linespacing=1.1)
        ax2.set_xlabel(f"championships, sorted by odds (n = {len(gc)})")
        ax2.set_title("C  Same rule, different odds", loc="left", x=-t2, fontsize=fs_title)
        ax2.legend(handles=[h_p0, h_p1, h_p2], loc="upper right", frameon=False, handletextpad=0.3,
                   borderaxespad=0.2, labelspacing=0.3, handlelength=1.5)
        fig.text(0.08 / W, 0.04 / H, "B: each championship's own fit. C: shared distribution shifted by offset "
                                     "(simulated).", fontsize=6.0, color=INK2, ha="left", va="bottom")
        save_fig(fig, args.out, _mock(sj, gj, fj))


def fig_rt_hist(args):
    import matplotlib.pyplot as plt
    desc = load(args.descriptive)
    h = T(desc, "hist_2ms")
    fig, ax = plt.subplots(figsize=(4.2, 2.8))
    for sex, col, mk in (("M", PAL["blue"], "o"), ("W", PAL["orange"], "s")):
        s = h[h["sex"] == sex]
        mid = (s["lo"] + s["hi"]) / 2
        ax.step(1000 * mid, s["count"], where="mid", color=col, lw=1.4, label={"M": "Men", "W": "Women"}[sex])
    ax.axvline(100, color=PAL["red"], lw=1.0)
    ax.text(101, ax.get_ylim()[1] * 0.92, "0.100 s", color=INK2, fontsize=7)
    ax.set_xlabel("Reaction time (ms), 2 ms bins")
    ax.set_ylabel("Starts")
    yr = f"{desc['numbers']['year_min']['value']}-{desc['numbers']['year_max']['value']}"
    ax.set_title(f"Championship RTs, {yr}", loc="left")
    ax.legend(loc="upper right")
    fig.tight_layout()
    save_fig(fig, args.out, _mock(desc))


def fig_terciles(args):
    import matplotlib.pyplot as plt
    fp = load(args.fp)
    t = T(fp, "by_comp_tercile")
    order = ["short", "mid", "long"]
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.2))
    for cy in sorted(t["comp_year"].unique()):
        s = t[t["comp_year"] == cy].set_index("tercile").loc[order]
        axes[0].plot(s["mean_fp_s"], s["mean_rt_ms"], color=COMP_COLOR.get(cy, MUTED), marker=COMP_MARK.get(cy, "o"),
                     lw=1.6, ms=5, label=cy)
        axes[1].plot(s["mean_fp_s"], 100 * s["share_lt120"], color=COMP_COLOR.get(cy, MUTED),
                     marker=COMP_MARK.get(cy, "o"), lw=1.6, ms=5, label=cy)
    axes[0].set_xlabel("Mean Seiko Ready Time in tercile (s)")
    axes[0].set_ylabel("Mean valid RT (ms)")
    axes[0].set_title("A  Mean RT by Ready Time tercile", loc="left")
    axes[1].set_xlabel("Mean Seiko Ready Time in tercile (s)")
    axes[1].set_ylabel("Valid RTs < 0.120 s (%)")
    axes[1].set_title("B  Fast starts by Ready Time tercile", loc="left")
    axes[0].legend(loc="upper center", bbox_to_anchor=(1.1, -0.2), ncol=3, fontsize=7, frameon=False)
    fig.tight_layout()
    save_fig(fig, args.out, _mock(fp))


def fig_policies(args):
    import matplotlib.pyplot as plt
    f = load(args.fairness)
    pol = T(f, "policies")
    pol = pol[pol["sex"] == args.sex]
    fig, ax = plt.subplots(figsize=(6.4, 2.8))
    for i, (_, r) in enumerate(pol.iterrows()):
        ax.scatter(r["mean_shift_ms"], r["per_1000_avg"], color=SERIES[i], marker="osD^v"[i % 5], s=30, zorder=3,
                   edgecolor="white", linewidth=0.6, label=r["policy"])
    ax.set_xlabel("Mean RT change vs championship holds (ms)")
    ax.set_ylabel("Legitimate starts < 0.100 s\nper 1,000 (hazard model)")
    ax.set_yscale("log")
    ax.set_title("Starter hold policies (simulation)", loc="left")
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), fontsize=6, frameon=False)
    fig.tight_layout()
    save_fig(fig, args.out, _mock(f))


FIGS = {"power": fig_power, "fairness": fig_fairness, "holds": fig_holds, "story": fig_story, "story_wide": fig_story_wide, "confound": fig_confound, "rt_hist": fig_rt_hist,
        "terciles": fig_terciles, "policies": fig_policies}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fig", required=True, choices=sorted(FIGS))
    ap.add_argument("--out", required=True)
    ap.add_argument("--power")
    ap.add_argument("--descriptive")
    ap.add_argument("--fairness")
    ap.add_argument("--fp")
    ap.add_argument("--systematic")
    ap.add_argument("--guardband")
    ap.add_argument("--fignums")
    ap.add_argument("--sex", default="M")
    args = ap.parse_args()
    set_style()
    FIGS[args.fig](args)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
