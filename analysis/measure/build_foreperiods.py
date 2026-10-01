"""Assemble data/derived/foreperiods.csv (one row per measured start attempt) from the measured starts and the
blind manual annotations.

Usage:
  python analysis/measure/build_foreperiods.py --measured analysis/measure/results/starts_measured.csv \
      --manual analysis/measure/manual_annotations.csv --override-ms 40 --out data/derived/foreperiods.csv

Rules:
  * method 'audio_auto_v1': the automated measurement (default).
  * method 'manual_override': a clean manual reading exists and differs from the automated set onset or gun by
    more than --override-ms; the manual times are used (uncertainty = sqrt(reading_unc^2 + 5 ms^2)).
  * The manual reader judged the "Set" command not identifiable (clean = 0): foreperiod left blank,
    qc_flag 'set_not_identifiable'; the automated value is kept in notes for transparency.
  * Starts without a blind reading but with a non-blind visual verdict (verification_visual.csv, gross-error
    screening of the automated marks): 'ok' -> manual_check 'visual_ok'; 'corrected' -> corrected times, method
    'visual_override', uncertainty sqrt(20^2 + 5^2) ms; 'unidentifiable' -> blank foreperiod.
  * manual_check: 'agree' (|auto - manual| <= override-ms), 'override', 'unidentifiable', 'visual_ok',
    'visual_corrected', 'visual_unidentifiable', or 'not_checked'.
  * When no /s/ frication is visible (vowel_onset_only = 1 in either review file, or qc flag weak_s_onset) the
    onset is the vowel onset, biased late by the /s/ duration: 0.10 s is added in quadrature to the uncertainty
    and the flag weak_s_onset is set.
Times (set_onset_s, gun_s) are seconds from the start of the source recording (see url, which also carries a
t= parameter near the start). Real broadcast audio only.
"""
import argparse

import numpy as np
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--measured", required=True)
    ap.add_argument("--manual", required=True)
    ap.add_argument("--visual", default=None)
    ap.add_argument("--override-ms", type=float, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    m = pd.read_csv(a.measured)
    man = pd.read_csv(a.manual)
    man = man[man.attempt_status != "not_a_start"]
    d = m.merge(man[["race_id", "attempt", "t_set_on", "t_voicing_end", "t_gun", "set_on_read_unc_s", "clean", "notes",
                     "vowel_onset_only"]],
                on=["race_id", "attempt"], how="left", suffixes=("", "_man"))
    thr = a.override_ms / 1000
    vis = {}
    if a.visual:
        for _, v in pd.read_csv(a.visual).iterrows():
            vis[(v.race_id, int(v.attempt))] = v
    rows = []
    for _, r in d.iterrows():
        url = f"https://www.youtube.com/watch?v={r.video_id}&t={max(0, int(float(r.t_gun_hint) - 10))}s"
        base = dict(race_id=r.race_id, attempt=int(r.attempt), attempt_status=r.attempt_status, video_id=r.video_id, url=url)
        if isinstance(r.fail, str) and r.fail:
            rows.append({**base, "foreperiod_s": None, "set_onset_s": None, "gun_s": None, "method": "none",
                         "uncertainty_s": None, "foreperiod_offset_s": None, "set_offset_s": None,
                         "qc_flag": "measurement_failed", "manual_check": "not_checked", "set_snr_db": None,
                         "notes": f"automated measurement failed: {r.fail}"})
            continue
        row = {**base, "foreperiod_s": r.fp_on_s, "set_onset_s": r.t_set_on, "gun_s": r.t_gun, "method": "audio_auto_v1",
               "uncertainty_s": r.unc_on_s, "foreperiod_offset_s": r.fp_off_s, "set_offset_s": r.t_set_off,
               "qc_flag": r.qc_flag, "manual_check": "not_checked", "set_snr_db": r.set_snr_db, "notes": ""}
        v = vis.get((r.race_id, int(r.attempt)))
        if pd.isna(r.clean) and v is not None:
            if v.verdict == "ok":
                row.update(manual_check="visual_ok", notes="automated marks confirmed on a non-blind verification sheet")
            elif v.verdict == "corrected":
                row.update(foreperiod_s=round(v.t_gun - v.t_set_on, 4), set_onset_s=v.t_set_on, gun_s=v.t_gun,
                           method="visual_override", uncertainty_s=round(float(np.sqrt(0.02 ** 2 + 0.005 ** 2)), 4),
                           foreperiod_offset_s=None, set_offset_s=None, manual_check="visual_corrected",
                           notes=f"automated marks wrong on verification sheet ({v.notes}); auto fp_on was {r.fp_on_s:.3f} s")
            elif v.verdict == "unidentifiable":
                row.update(foreperiod_s=None, set_onset_s=None, foreperiod_offset_s=None, set_offset_s=None, method="none",
                           uncertainty_s=None, qc_flag="set_not_identifiable", manual_check="visual_unidentifiable",
                           notes=f"verification sheet: {v.notes}; automated fp_on was {r.fp_on_s:.3f} s")
        if pd.notna(r.clean):
            if int(r.clean) == 0:
                row.update(foreperiod_s=None, set_onset_s=None, foreperiod_offset_s=None, set_offset_s=None, method="none",
                           uncertainty_s=None, qc_flag="set_not_identifiable", manual_check="unidentifiable",
                           notes=f"manual: {r.notes}; automated fp_on was {r.fp_on_s:.3f} s")
            else:
                d_on = abs(r.t_set_on - r.t_set_on_man)
                d_gun = abs(r.t_gun - r.t_gun_man)
                if d_on > thr or d_gun > thr:
                    unc = float(np.sqrt((r.set_on_read_unc_s if pd.notna(r.set_on_read_unc_s) else 0.02) ** 2 + 0.005 ** 2))
                    row.update(foreperiod_s=round(r.t_gun_man - r.t_set_on_man, 4), set_onset_s=r.t_set_on_man,
                               gun_s=r.t_gun_man, method="manual_override", uncertainty_s=round(unc, 4),
                               foreperiod_offset_s=round(r.t_gun_man - r.t_voicing_end, 4) if pd.notna(r.t_voicing_end) else None,
                               set_offset_s=r.t_voicing_end, manual_check="override",
                               notes=f"automated differed from blind manual reading by {1000 * max(d_on, d_gun):.0f} ms "
                                     f"(auto fp_on {r.fp_on_s:.3f} s); manual used")
                else:
                    row.update(manual_check="agree",
                               notes=f"blind manual reading agrees within {a.override_ms:.0f} ms (manual fp_on "
                                     f"{r.t_gun_man - r.t_set_on_man:.3f} s)")
        weak = (pd.notna(r.get("vowel_onset_only")) and int(r.vowel_onset_only) == 1) or                (v is not None and int(v.vowel_onset_only) == 1) or "weak_s_onset" in str(row["qc_flag"])
        if weak and pd.notna(row["foreperiod_s"]):
            row["uncertainty_s"] = round(float(np.sqrt(float(row["uncertainty_s"]) ** 2 + 0.10 ** 2)), 4)
            if "weak_s_onset" not in str(row["qc_flag"]):
                row["qc_flag"] = "weak_s_onset" if row["qc_flag"] == "ok" else row["qc_flag"] + ";weak_s_onset"
            row["notes"] = (row["notes"] + "; " if row["notes"] else "") + "no visible /s/: onset = vowel onset (+0.10 s uncertainty)"
        rows.append(row)
    out = pd.DataFrame(rows)
    cols = ["race_id", "foreperiod_s", "set_onset_s", "gun_s", "method", "uncertainty_s", "qc_flag", "url", "notes",
            "attempt", "attempt_status", "foreperiod_offset_s", "set_offset_s", "manual_check", "set_snr_db", "video_id"]
    out = out[cols].sort_values(["race_id", "attempt"])
    out.to_csv(a.out, index=False, lineterminator="\n", float_format="%.4f")


if __name__ == "__main__":
    main()
