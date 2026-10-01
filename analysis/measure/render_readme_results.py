"""Render the generated validation-results section of analysis/measure/README.md from results artifacts.

Usage:
  python analysis/measure/render_readme_results.py --readme analysis/measure/README.md \
      --seiko analysis/measure/results/seiko_validation.json --dev analysis/measure/results/auto_vs_manual_dev.json \
      [--heldout analysis/measure/results/auto_vs_manual_heldout.json] \
      [--synthetic analysis/measure/results/benchmark_synthetic_summary.json] --out analysis/measure/README.md
Replaces the text between the BEGIN/END GENERATED RESULTS markers; nothing else is touched.
"""
import argparse
import json
import os

BEGIN = "<!-- BEGIN GENERATED RESULTS (render_readme_results.py; do not edit by hand) -->"
END = "<!-- END GENERATED RESULTS -->"


def load(p):
    return json.load(open(p, encoding="utf-8")) if p and os.path.exists(p) else None


def ms(v):
    return "n/a" if v is None else f"{1000 * v:.0f}"


def pct(v):
    return "n/a" if v is None else f"{100 * v:.0f}%"


def seiko_section(s):
    L = ["### (c) Real broadcasts vs official Seiko Ready Time",
         "",
         f"Valid (final) start attempts with a validated Ready Time and a clean \"Set\": **n = {s['n_compared']}** "
         f"of {s['n_valid_starts_annotated']} annotated. d = broadcast foreperiod - Ready Time.",
         "",
         "| broadcast reference point | n | bias (ms) | SD (ms) | MAE (ms) | min (ms) | max (ms) | within +-20 ms | within +-40 ms |",
         "|---|---|---|---|---|---|---|---|---|"]
    rows = [("set onset (manual)", s["manual"]["onset_minus_ready"]),
            ("end of voicing (manual)", s["manual"]["voicing_end_minus_ready"]),
            ("end of word incl. /t/ (manual)", s["manual"]["word_end_minus_ready"]),
            ("set onset (automated)", s["automated"]["onset_minus_ready"]),
            ("set offset (automated)", s["automated"]["offset_minus_ready"])]
    for name, v in rows:
        L.append(f"| {name} | {v['n']} | {ms(v['bias_s'])} | {ms(v['sd_s'])} | {ms(v['mae_s'])} | {ms(v['min_s'])} | "
                 f"{ms(v['max_s'])} | {pct(v['within_20ms'])} | {pct(v['within_40ms'])} |")
    fd = s.get("final_dataset_valid")
    if fd:
        v = fd["onset_minus_ready"]
        c2 = fd["corr_ready_vs_fp_onset"]
        L += ["", f"**Final dataset** (all reviewed valid starts in foreperiods.csv with a validated Ready Time, n = {fd['n']}): "
                  f"onset foreperiod - Ready = {ms(v['bias_s'])} ms mean (SD {ms(v['sd_s'])} ms, range {ms(v['min_s'])} to "
                  f"{ms(v['max_s'])} ms; within +-40 ms: {pct(v['within_40ms'])}). Within-championship residual SD "
                  f"{ms(fd['within_championship_sd_s'])} ms, MAD {ms(fd['within_championship_mad_s'])} ms, "
                  f"{pct(fd['within_championship_share_resid_le_100ms'])} of residuals within 100 ms. "
                  f"r(Ready, onset foreperiod) = {c2.get('r')} (95% CI {c2.get('r_ci95')}).", "",
              "| championship (final dataset) | n | onset - Ready: mean (ms) | SD (ms) | min (ms) | max (ms) |", "|---|---|---|---|---|---|"]
        for comp, w in sorted(fd["onset_minus_ready_by_championship"].items()):
            L.append(f"| {comp} | {w['n']} | {ms(w['bias_s'])} | {ms(w['sd_s'])} | {ms(w['min_s'])} | {ms(w['max_s'])} |")
    L += ["", "| championship (blind manual subset) | n | onset - Ready: mean (ms) | SD (ms) | voicing end - Ready: mean (ms) |", "|---|---|---|---|---|"]
    on = s["manual"]["onset_minus_ready_by_championship"]
    ve = s["manual"]["voicing_end_minus_ready_by_championship"]
    for comp in sorted(on):
        L.append(f"| {comp} | {on[comp]['n']} | {ms(on[comp]['bias_s'])} | {ms(on[comp]['sd_s'])} | {ms(ve[comp]['bias_s'])} |")
    c = s["manual"]["corr_ready_vs_fp_onset"]
    L += ["",
          f"Within-championship SD of (onset - Ready) after removing each championship's mean: "
          f"{ms(s['manual']['onset_minus_ready_within_championship_sd_s'])} ms "
          f"(voicing end: {ms(s['manual']['voicing_end_minus_ready_within_championship_sd_s'])} ms). "
          f"Pearson r(Ready Time, onset foreperiod) = {c.get('r')} (95% CI {c.get('r_ci95')}), "
          f"OLS slope {c.get('ols_ready_on_fp_slope')}.",
          "",
          "Excluded (listed, not dropped silently):"]
    for e in s["excluded"]:
        L.append(f"- {e['race_id']} attempt {e['attempt']}: {e['reason']}")
    return L


def agree_section(d, title):
    L = [f"### {title}", "", f"Starts matched: {d['n_starts_matched']}; clean \"Set\": {d['n_clean']}. Error = automated - manual.", "",
         "| quantity | n | bias (ms) | MAE (ms) | max abs (ms) | within +-10 ms | within +-20 ms | within +-40 ms |",
         "|---|---|---|---|---|---|---|---|"]
    for name, k in (("gun onset (all matched starts)", "gun_onset"), ("set onset (clean)", "set_onset_clean"),
                    ("foreperiod, onset-based (clean)", "fp_onset_clean"),
                    ("set offset vs manual end of voicing (clean)", "set_offset_vs_voicing_end_clean")):
        v = d[k]
        if v.get("n", 0) == 0:
            continue
        L.append(f"| {name} | {v['n']} | {v['bias_ms']:.1f} | {v['mae_ms']:.1f} | {v['max_abs_ms']:.1f} | "
                 f"{pct(v['within_10ms'])} | {pct(v['within_20ms'])} | {pct(v['within_40ms'])} |")
    return L


def synthetic_section(syn):
    if not syn:
        return ["### (a) Synthetic benchmark (SIMULATED audio)", "", "Not yet run for this version; see `benchmark_synthetic.py`."]
    h, q = syn.get("headline", {}), syn.get("qc", {})
    L = ["### (a) Synthetic benchmark (SIMULATED audio; known ground truth)", "", syn.get("description", ""), "",
         f"Headline (SIMULATED): realistic backgrounds (hold, pink) at SNR >= +10 dB: n = {h.get('realistic_snr_ge_10_n')}, "
         f"gross errors {pct(h.get('realistic_snr_ge_10_gross'))}, foreperiod bias {h.get('realistic_snr_ge_10_fp_bias_ms')} ms, "
         f"MAE {h.get('realistic_snr_ge_10_fp_mae_ms')} ms, within +-20 ms {pct(h.get('realistic_snr_ge_10_within_20ms'))}, "
         f"within +-40 ms {pct(h.get('realistic_snr_ge_10_within_40ms'))}. All realistic trials: gross {pct(h.get('realistic_gross'))}; "
         f"stress backgrounds (race crowd, commentary): gross {pct(h.get('stress_gross'))}. Gun MAE (non-gross) "
         f"{h.get('gun_mae_ms_nongross')} ms. QC: {pct(q.get('share_qc_ok'))} of trials pass all flags; gross-error rate "
         f"{pct(q.get('gross_rate_if_qc_ok'))} when qc_flag is ok vs {pct(q.get('gross_rate_if_flagged'))} when flagged.", "",
         "| condition | n | detected | gross errors | fp bias (ms) | fp MAE (ms) | within +-20 ms | within +-40 ms |",
         "|---|---|---|---|---|---|---|---|"]
    for row in syn.get("table", []):
        L.append(f"| {row['condition']} | {row['n']} | {pct(row['detected'])} | {pct(row['gross'])} | {row['bias_ms']:.1f} | "
                 f"{row['mae_ms']:.1f} | {pct(row['within_20ms'])} | {pct(row['within_40ms'])} |")
    return L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--readme", required=True)
    ap.add_argument("--seiko", required=True)
    ap.add_argument("--dev", required=True)
    ap.add_argument("--heldout", default=None)
    ap.add_argument("--synthetic", default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    txt = open(a.readme, encoding="utf-8").read()
    i0, i1 = txt.index(BEGIN), txt.index(END)
    L = [BEGIN, ""]
    L += synthetic_section(load(a.synthetic)) + [""]
    L += agree_section(load(a.dev), "(b) Real broadcasts: automated vs blind manual reading, DEV split (in-sample)") + [""]
    ho = load(a.heldout)
    if ho:
        L += agree_section(ho, "(b) Real broadcasts: automated vs blind manual reading, HELD-OUT split (detector frozen)") + [""]
    else:
        L += ["### (b) Held-out split", "", "Not yet annotated.", ""]
    L += seiko_section(load(a.seiko)) + [""]
    new = txt[:i0] + "\n".join(L) + txt[i1:]
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(new)


if __name__ == "__main__":
    main()
