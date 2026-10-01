# Data correction (2026-10-01): one calibration start was mislabelled

**What was wrong.** In the women's 100 m session video (World Athletics upload `2McuUM2729o`), the start at 2597.6 s
had been labelled the final (`WCH2025-100m-W-F-H1`) by the automated video matcher ("top-ranked candidate; final"). The
L1 footage check (`notes/lane_confirmatory/L1_report.md`) showed it is semi-final 3 (`WCH2025-100m-W-SF-H3`); the
final's start comes later in the video and was never measured. The audio foreperiod of semi-final 3 had therefore been
paired with the final's Seiko Ready Time (1.620 s) in one of the 22 calibration pairs and in the held-out reading H01.

**Fix.** The label was corrected at its source (`analysis/measure/race_starts_curated.csv`) and in the three files that
carried it (`annotation_key_heldout.csv`, `manual_annotations.csv`, `results/starts_measured.csv`); the pair is now
matched to semi-final 3's own validated Ready Time (1.661 s). Every downstream step was rerun in dependency order
(measure validations and numbers, `foreperiods.csv`, `video_sources.csv`, then calibration, fairness, systematic,
guardband, trend, figure numbers, figures, numbers.json and results.md) and each output was re-verified byte for byte.

**Effect.** 73 of 1154 numbers changed, all slightly (calibration, measurement validation, fairness,
four secondary foreperiod-scale systematic numbers, trend). No pre-registered verdict changed. The only abstract number
affected is the calibration offset, 0.5232 s -> 0.5214 s, which still prints as 0.52 s; the rendered abstract text and
all three figures are unchanged.

Rows whose before and after values match changed only in other fields (intervals or descriptions); every verdict
string is identical.

| key | before | after |
|---|---|---|
| `calibration.calib_slope_b` | 0.8156 | 0.8204 |
| `calibration.calib_slope_b_voice_end` | 0.8847 | 0.8909 |
| `calibration.corr_ready_audio` | 0.7448 | 0.7513 |
| `calibration.direct_audio_slope_ms_per_100ms` | 1.019 | 1.009 |
| `calibration.offset_mean_WCH2025_s` | 0.6099 | 0.6072 |
| `calibration.offset_mean_s` | 0.5232 | 0.5214 |
| `calibration.offset_sd_within_comp_s` | 0.1121 | 0.1103 |
| `calibration.r_ci_high_at_b_low` | 0.113 | 0.1123 |
| `calibration.r_ci_low_at_b_low` | -0.021 | -0.0209 |
| `calibration.r_corrected` | 0.0392 | 0.0391 |
| `calibration.slope_corrected_ms_per_100ms` | 0.397 | 0.395 |
| `fairness.cal_max_fold_change_corrected` | 3.894 | 3.879 |
| `fairness.cal_max_fold_change_corrected_b_low` | 4.925 | 4.876 |
| `measure.real_seiko_auto_onset_minus_ready_bias_s` | 0.5239 | 0.522 |
| `measure.real_seiko_auto_onset_minus_ready_sd_s` | 0.1658 | 0.164 |
| `measure.real_seiko_autoall_corr_r` | 0.6784 | 0.6801 |
| `measure.real_seiko_autoall_corr_r_ci95` | [0.4652, 0.8172] | [0.4676, 0.8182] |
| `measure.real_seiko_autoall_onset_minus_ready_bias_s` | 0.5544 | 0.5533 |
| `measure.real_seiko_autoall_onset_minus_ready_sd_s` | 0.2241 | 0.2236 |
| `measure.real_seiko_corr_ready_fp_onset_r` | 0.7448 | 0.7513 |
| `measure.real_seiko_corr_ready_fp_onset_r_ci95` | [0.4712, 0.8877] | [0.4826, 0.8908] |
| `measure.real_seiko_final_WCH2025_bias_s` | 0.6413 | 0.6398 |
| `measure.real_seiko_final_WCH2025_sd_s` | 0.2132 | 0.213 |
| `measure.real_seiko_final_corr_r` | 0.6823 | 0.6839 |
| `measure.real_seiko_final_corr_r_ci95` | [0.4709, 0.8196] | [0.4732, 0.8206] |
| `measure.real_seiko_final_ols_slope` | 0.6133 | 0.6146 |
| `measure.real_seiko_final_onset_minus_ready_bias_s` | 0.5568 | 0.5558 |
| `measure.real_seiko_final_onset_minus_ready_sd_s` | 0.2253 | 0.2247 |
| `measure.real_seiko_final_within_champ_mad_s` | 0.1005 | 0.099 |
| `measure.real_seiko_final_within_champ_sd_s` | 0.1831 | 0.1829 |
| `measure.real_seiko_onset_minus_ready_WCH2025_bias_s` | 0.6099 | 0.6072 |
| `measure.real_seiko_onset_minus_ready_WCH2025_sd_s` | 0.1173 | 0.115 |
| `measure.real_seiko_onset_minus_ready_bias_s` | 0.5232 | 0.5214 |
| `measure.real_seiko_onset_minus_ready_mae_s` | 0.5232 | 0.5214 |
| `measure.real_seiko_onset_minus_ready_sd_s` | 0.171 | 0.169 |
| `measure.real_seiko_onset_within_champ_sd_s` | 0.1066 | 0.105 |
| `measure.real_seiko_voicingend_minus_ready_WCH2025_bias_s` | 0.2471 | 0.2443 |
| `measure.real_seiko_voicingend_minus_ready_bias_s` | 0.1626 | 0.1607 |
| `measure.real_seiko_voicingend_minus_ready_mae_s` | 0.196 | 0.1941 |
| `measure.real_seiko_voicingend_minus_ready_sd_s` | 0.1599 | 0.1574 |
| `measure.real_seiko_voicingend_within_champ_sd_s` | 0.096 | 0.0935 |
| `measure.real_seiko_wordend_minus_ready_bias_s` | 0.1212 | 0.1194 |
| `measure.real_seiko_wordend_minus_ready_sd_s` | 0.1705 | 0.1677 |
| `systematic.h1c_r_pooled_fp` | 0.3737 | 0.3729 |
| `systematic.h1d_pearson_fp_3` | 0.9966 | 0.9964 |
| `systematic.h1s1_fp_beta0_r_mean` | 0.3145 | 0.3142 |
| `systematic.h1s1_fp_betahat_r_mean` | 0.3322 | 0.332 |
| `trend.s4_full_lr_estimate` | 4006.0 | 4033.0 |
| `trend.s4_full_lr_upper` | 10.61 | 11.02 |
| `trend.s4_full_p_pooled_estimate` | 0.003239 | 0.003217 |
| `trend.s4_full_p_pooled_upper` | 0.01195 | 0.01184 |
| `trend.s4_full_p_within_estimate` | 8.085e-07 | 7.976e-07 |
| `trend.s4_full_p_within_upper` | 0.001126 | 0.001074 |
| `trend.s4_lenient_p_pooled_estimate` | 0.0185 | 0.01844 |
| `trend.s4_lenient_p_pooled_upper` | 0.1214 | 0.1197 |
| `trend.s4_lenient_p_within_estimate` | 1.164e-06 | 1.148e-06 |
| `trend.s4_lenient_p_within_upper` | 0.003523 | 0.003322 |
| `trend.s4_litsd_p_pooled_estimate` | 0.0325 | 0.03225 |
| `trend.s4_litsd_p_pooled_upper` | 0.177 | 0.1752 |
| `trend.s4_litsd_p_within_estimate` | 1.322e-06 | 1.306e-06 |
| `trend.s4_litsd_p_within_upper` | 0.00402 | 0.003801 |
| `trend.s4_lr_estimate` | 18460.0 | 18650.0 |
| `trend.s4_lr_upper` | 41.77 | 43.61 |
| `trend.s4_p_pooled_estimate` | 0.0175 | 0.01744 |
| `trend.s4_p_pooled_upper` | 0.1164 | 0.1146 |
| `trend.s4_p_within_estimate` | 9.48e-07 | 9.349e-07 |
| `trend.s4_p_within_upper` | 0.002787 | 0.002628 |
| `trend.s4_r_star` | 0.1554 | 0.1554 |
| `trend.s4_rw_estimate` | 0.0392 | 0.0391 |
| `trend.s4_rw_upper` | 0.113 | 0.1123 |
| `trend.s4_verdict` | WITHIN-CHAMPIONSHIP ANALYSIS STATISTICALLY IMPLAUSIBLE | WITHIN-CHAMPIONSHIP ANALYSIS STATISTICALLY IMPLAUSIBLE |
| `trend.s4_verdict_inversion` | WITHIN READING NEEDS r_w ABOVE OUR CI | WITHIN READING NEEDS r_w ABOVE OUR CI |
| `trend.s4_verdict_lr` | FAVOURS POOLED | FAVOURS POOLED |
