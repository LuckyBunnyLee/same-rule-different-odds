# Planning calc only (NOT a paper result). Power to detect a race-level FP slope on mean RT
# using race-mean OLS. Assumptions (labelled guesses): 8 athletes/race, within-race SD 20 ms,
# race random-effect SD 8 ms, FP ~ N(1.78, 0.158) s (Otsuka et al. 2017 championship estimate).
import numpy as np
rng = np.random.default_rng(1)
def power(n_races, slope_ms_per_s, reps=4000, k=8, sd_w=20, sd_r=8, fp_sd=0.158):
    hits = 0
    for _ in range(reps):
        fp = rng.normal(1.78, fp_sd, n_races)
        race_eff = rng.normal(0, sd_r, n_races)
        means = 150 + slope_ms_per_s*(fp-1.78) + race_eff + rng.normal(0, sd_w/np.sqrt(k), n_races)
        X = np.column_stack([np.ones(n_races), fp-1.78])
        beta, res, *_ = np.linalg.lstsq(X, means, rcond=None)
        resid = means - X@beta
        s2 = resid@resid/(n_races-2)
        se = np.sqrt(s2*np.linalg.inv(X.T@X)[1,1])
        hits += abs(beta[1]/se) > 1.98
    return hits/reps
for slope in [22, 40, 62]:
    print(slope, 'ms/s:', {n: round(power(n, slope),2) for n in [40, 60, 85, 120, 200]})
