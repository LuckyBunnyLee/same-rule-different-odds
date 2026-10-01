"""Literature audit: how much of the published championship-RT literature uses designs exposed to
championship-level variation (protocol: lit/audit_protocol.md, committed before any study was coded).

Reads
  --studies     lit/audit_studies.csv            one row per coded finding (primary studies and grey literature)
  --screening   lit/audit_screening.csv          screening decisions for every de-duplicated search record
  --search-log  lit/audit_search/search_log.json per-source queries and hit counts
and writes one deterministic result JSON (result name "audit", so make_numbers keys arrive as audit.*).

The protocol's rule is recomputed here, never trusted from the CSV: a finding is vulnerable if its design class is
P, S or E, or M with m_averages_venues = yes. The script stops if the stored `vulnerable` column disagrees, if the
coding vocabulary is broken, if a conflict group does not hold a real disagreement, or if the screening table and
the coded studies do not match.

Usage (repo root):
  .venv\\Scripts\\python.exe analysis\\lit_audit.py --studies lit/audit_studies.csv --screening lit/audit_screening.csv
      --search-log lit/audit_search/search_log.json --out analysis/outputs/lit_audit.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from common import ROOT, num, write_result

NAME = "audit"
CLASSES = ["P", "S", "E", "M", "W", "U"]
VULNERABLE_CLASSES = {"P", "S", "E"}
EFFECTS = ["hold_foreperiod", "rule_era", "sex", "threshold_limit", "lane", "round", "performance_correlation", "other"]
TAGS = {"V-FT", "V-ABS", "S", "U"}
VERIFIED = {"V-FT", "V-ABS"}
YES_NO_UNCLEAR = {"yes", "no", "unclear"}
STUDY_FIELDS = ["in_primary", "citation", "year", "doi", "pub_type", "access", "data_source", "championships",
                "n_championships", "events"]
REQUIRED = ["study_id", "finding_id", *STUDY_FIELDS, "finding", "effect_type", "design_class", "m_averages_venues",
            "conclusion_scope", "depends_on_between_contrast", "vulnerable", "reports_champ_difference",
            "conflict_group", "direction", "verification_tag", "design_tag", "notes"]
RULE = ("vulnerable = design class P, S or E, or M with m_averages_venues = yes; "
        "W, M (not averaging) and U are not vulnerable in the primary count")


class AuditError(SystemExit):
    pass


def vulnerable_rule(design_class: str, m_averages_venues: str) -> bool:
    """lit/audit_protocol.md section 6."""
    return design_class in VULNERABLE_CLASSES or (design_class == "M" and m_averages_venues == "yes")


def load(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")


def validate(df: pd.DataFrame, screening: pd.DataFrame) -> list[str]:
    """Return a list of problems (empty when the coding obeys the protocol)."""
    errs: list[str] = []
    miss = [c for c in REQUIRED if c not in df.columns]
    if miss:
        return [f"missing columns: {miss}"]
    if df["finding_id"].duplicated().any():
        errs.append(f"duplicate finding_id: {sorted(df.loc[df['finding_id'].duplicated(), 'finding_id'])}")
    for sid, g in df.groupby("study_id"):
        for c in STUDY_FIELDS:
            if g[c].nunique() > 1:
                errs.append(f"{sid}: study field {c} differs between findings")
    checks = [("design_class", set(CLASSES)), ("effect_type", set(EFFECTS)), ("in_primary", {"yes", "no"}),
              ("m_averages_venues", {"yes", "no", "na"}), ("depends_on_between_contrast", YES_NO_UNCLEAR),
              ("vulnerable", {"yes", "no"}), ("reports_champ_difference", {"yes", "no"}),
              ("verification_tag", TAGS), ("design_tag", TAGS),
              ("conclusion_scope", {"generalised", "restricted", "unclear"})]
    for col, allowed in checks:
        bad = df.loc[~df[col].isin(allowed), ["finding_id", col]]
        for _, r in bad.iterrows():
            errs.append(f"{r['finding_id']}: {col} = {r[col]!r} not in {sorted(allowed)}")
    for _, r in df.iterrows():
        fid, cls, mavg = r["finding_id"], r["design_class"], r["m_averages_venues"]
        if cls == "M" and mavg not in ("yes", "no"):
            errs.append(f"{fid}: class M needs m_averages_venues yes/no")
        if cls != "M" and mavg != "na":
            errs.append(f"{fid}: m_averages_venues must be 'na' unless class M")
        want = "yes" if vulnerable_rule(cls, mavg) else "no"
        if r["vulnerable"] != want:
            errs.append(f"{fid}: stored vulnerable={r['vulnerable']} but the protocol rule gives {want}")
        k = r["n_championships"].strip()
        if k == "1" and cls in ("P", "E", "M"):
            errs.append(f"{fid}: class {cls} needs >= 2 championships, coded k = 1")
        if cls in ("S", "W") and k != "1":
            errs.append(f"{fid}: class {cls} is single-championship, coded k = {k!r}")
        if cls == "S" and r["conclusion_scope"] != "generalised":
            errs.append(f"{fid}: class S needs a generalised conclusion")
        if cls == "W" and r["conclusion_scope"] != "restricted":
            errs.append(f"{fid}: class W needs a restricted conclusion")
        if r["conflict_group"]:
            if r["conflict_group"] != r["effect_type"]:
                errs.append(f"{fid}: conflict_group {r['conflict_group']!r} must equal its effect_type")
            if not r["direction"]:
                errs.append(f"{fid}: conflict-group member without a stated direction")
    prim = df[df["in_primary"] == "yes"]
    for grp, g in prim[prim["conflict_group"] != ""].groupby("conflict_group"):
        if g["study_id"].nunique() < 2:
            errs.append(f"conflict group {grp}: fewer than 2 studies")
        if g["direction"].nunique() < 2:
            errs.append(f"conflict group {grp}: no disagreement (single direction {sorted(set(g['direction']))})")
    inc = set(screening.loc[screening["decision"] == "include", "study_id"])
    grey = set(screening.loc[(screening["reason"] == "E-TYPE") & (screening["study_id"] != ""), "study_id"])
    coded_p = set(prim["study_id"])
    coded_g = set(df.loc[df["in_primary"] == "no", "study_id"])
    if inc != coded_p:
        errs.append(f"screening includes vs coded primary studies differ: only screened {sorted(inc - coded_p)}, "
                    f"only coded {sorted(coded_p - inc)}")
    if grey != coded_g:
        errs.append(f"screening E-TYPE vs coded grey studies differ: {sorted(grey ^ coded_g)}")
    return errs


def study_flags(f: pd.DataFrame, mask: pd.Series) -> pd.Series:
    """Per study: does at least one finding satisfy `mask`?"""
    return mask.groupby(f["study_id"]).any()


def compute(df: pd.DataFrame, screening: pd.DataFrame, log: dict) -> tuple[dict, dict, dict]:
    prim = df[df["in_primary"] == "yes"].copy()
    vul = prim["vulnerable"].eq("yes")
    n_st = prim["study_id"].nunique()
    k_st = int(study_flags(prim, vul).sum())
    n_f, k_f = len(prim), int(vul.sum())
    numbers = {
        "n_studies": num(n_st, desc="included studies analysing official championship RTs (primary set)", unit="studies"),
        "k_vulnerable_studies": num(k_st, desc="studies with >= 1 vulnerable finding (P, S, E or venue-averaging M)",
                                    unit="studies"),
        "share_vulnerable_studies": num(k_st / n_st, desc="K / N", unit="share"),
        "pct_vulnerable_studies": num(round(100 * k_st / n_st), desc="K / N in whole percent", unit="%"),
        "n_findings": num(n_f, desc="coded findings in the primary set", unit="findings"),
        "k_vulnerable_findings": num(k_f, desc="vulnerable findings in the primary set", unit="findings"),
        "share_vulnerable_findings": num(k_f / n_f, desc="vulnerable / all coded findings", unit="share"),
        "pct_vulnerable_findings": num(round(100 * k_f / n_f), desc="vulnerable / all findings, whole percent", unit="%"),
    }
    # by design class
    for c in CLASSES:
        numbers[f"findings_class_{c}"] = num(int((prim["design_class"] == c).sum()), desc=f"findings coded class {c}",
                                             unit="findings")
        numbers[f"studies_class_{c}"] = num(int(study_flags(prim, prim["design_class"] == c).sum()),
                                            desc=f"studies with >= 1 class-{c} finding", unit="studies")
    mavg = (prim["design_class"] == "M") & (prim["m_averages_venues"] == "yes")
    numbers["findings_class_M_avg"] = num(int(mavg.sum()), desc="class-M findings whose conclusion averages over venues",
                                          unit="findings")
    numbers["findings_rule_era_class_E"] = num(int(((prim["effect_type"] == "rule_era") &
                                                    (prim["design_class"] == "E")).sum()),
                                               desc="rule-era findings coded E (era contrast, championships nested "
                                                    "in eras); equals findings_rule_era when every one is E",
                                               unit="findings")
    # by effect type
    for e in EFFECTS:
        m = prim["effect_type"] == e
        numbers[f"findings_{e}"] = num(int(m.sum()), desc=f"findings of effect type {e}", unit="findings")
        numbers[f"vulnerable_findings_{e}"] = num(int((m & vul).sum()), desc=f"vulnerable findings of effect type {e}",
                                                  unit="findings")
        numbers[f"studies_{e}"] = num(int(prim.loc[m, "study_id"].nunique()), desc=f"studies with a {e} finding",
                                      unit="studies")
        numbers[f"vulnerable_studies_{e}"] = num(int(prim.loc[m & vul, "study_id"].nunique()),
                                                 desc=f"studies with a vulnerable {e} finding", unit="studies")
    # conflicts
    cg = prim[prim["conflict_group"] != ""]
    groups = sorted(cg["conflict_group"].unique())
    numbers["n_conflict_groups"] = num(len(groups), desc="effect types on which >= 2 included studies disagree "
                                       "(opposite sign, significant vs null, or raise vs keep/lower 0.100 s)",
                                       unit="groups", groups=groups)
    numbers["findings_in_conflict_groups"] = num(len(cg), desc="findings in conflict groups", unit="findings")
    numbers["vulnerable_findings_in_conflict_groups"] = num(int(cg["vulnerable"].eq("yes").sum()),
                                                           desc="vulnerable findings in conflict groups", unit="findings")
    numbers["studies_in_conflict_groups"] = num(int(cg["study_id"].nunique()), desc="studies with a finding in a "
                                                "conflict group", unit="studies")
    numbers["vulnerable_studies_in_conflict_groups"] = num(int(cg.loc[cg["vulnerable"] == "yes", "study_id"].nunique()),
                                                          desc="studies with a vulnerable finding in a conflict group",
                                                          unit="studies")
    conflict_table = []
    for g in groups:
        sub = cg[cg["conflict_group"] == g]
        conflict_table.append({"group": g, "studies": int(sub["study_id"].nunique()), "findings": int(len(sub)),
                               "vulnerable_findings": int(sub["vulnerable"].eq("yes").sum()),
                               "directions": "; ".join(f"{d}: {', '.join(sorted(set(sub.loc[sub['direction'] == d, 'study_id'])))}"
                                                       for d in sorted(sub["direction"].unique()))})
        numbers[f"conflict_{g}_studies"] = num(int(sub["study_id"].nunique()), desc=f"studies in the {g} conflict group",
                                               unit="studies")
        numbers[f"conflict_{g}_vulnerable_studies"] = num(int(sub.loc[sub["vulnerable"] == "yes", "study_id"].nunique()),
                                                          desc=f"studies with a vulnerable finding in the {g} group",
                                                          unit="studies")
    # sensitivities
    strict = vul & prim["depends_on_between_contrast"].eq("yes")
    k_strict = int(study_flags(prim, strict).sum())
    numbers["k_strict_studies"] = num(k_strict, desc="studies with >= 1 vulnerable finding whose conclusion depends on "
                                      "a between-championship contrast", unit="studies")
    numbers["share_strict_studies"] = num(k_strict / n_st, desc="strict K / N", unit="share")
    numbers["k_strict_findings"] = num(int(strict.sum()), desc="vulnerable findings that depend on a between-"
                                       "championship contrast", unit="findings")
    u_vul = vul | prim["design_class"].eq("U")
    k_u = int(study_flags(prim, u_vul).sum())
    numbers["k_u_as_vulnerable_studies"] = num(k_u, desc="upper bound: class U also counted vulnerable", unit="studies")
    numbers["share_u_as_vulnerable_studies"] = num(k_u / n_st, desc="upper-bound K / N", unit="share")
    numbers["k_u_as_vulnerable_findings"] = num(int(u_vul.sum()), desc="upper bound on vulnerable findings",
                                                unit="findings")
    ver = prim[prim["design_tag"].isin(VERIFIED)]
    n_ver = ver["study_id"].nunique()
    k_ver = int(study_flags(ver, ver["vulnerable"].eq("yes")).sum())
    numbers["n_verified_only_studies"] = num(n_ver, desc="studies with >= 1 finding whose design coding rests on "
                                             "full text or abstract", unit="studies")
    numbers["k_verified_only_studies"] = num(k_ver, desc="vulnerable studies counting only findings whose design "
                                             "coding rests on full text or abstract", unit="studies")
    numbers["share_verified_only_studies"] = num(k_ver / n_ver if n_ver else float("nan"), desc="verified-only K / N",
                                                 unit="share")
    allg = df.copy()
    n_g = allg["study_id"].nunique()
    k_g = int(study_flags(allg, allg["vulnerable"].eq("yes")).sum())
    numbers["n_grey_added_studies"] = num(n_g, desc="primary plus coded grey-literature (E-TYPE) studies", unit="studies")
    numbers["k_grey_added_studies"] = num(k_g, desc="vulnerable studies with grey literature added", unit="studies")
    numbers["share_grey_added_studies"] = num(k_g / n_g, desc="grey-added K / N", unit="share")
    numbers["n_studies_reporting_champ_difference"] = num(
        int(study_flags(prim, prim["reports_champ_difference"].eq("yes")).sum()),
        desc="primary studies that themselves report an RT difference between championships", unit="studies")
    numbers["n_studies_single_championship"] = num(
        int(prim.groupby("study_id")["n_championships"].first().eq("1").sum()),
        desc="primary studies using one championship", unit="studies")
    vt = prim.groupby("study_id")["verification_tag"].agg(lambda s: "V-FT" if "V-FT" in set(s) else
                                                         ("V-ABS" if "V-ABS" in set(s) else
                                                          ("S" if "S" in set(s) else "U")))
    for t in ["V-FT", "V-ABS", "S", "U"]:
        numbers[f"studies_best_tag_{t.replace('-', '_')}"] = num(int((vt == t).sum()),
                                                                 desc=f"primary studies whose best source is {t}",
                                                                 unit="studies")
    closed = prim.groupby("study_id")["access"].first().str.startswith("closed")
    numbers["studies_closed_access"] = num(int(closed.sum()), desc="primary studies behind a paywall (coded from "
                                           "abstracts or secondary sources unless a copy was found)", unit="studies")
    # search and screening flow
    for src, v in log.items():
        numbers[f"search_{src}_reported"] = num(v.get("reported_count"), desc=f"hits reported by {src}", unit="records")
        numbers[f"search_{src}_saved"] = num(v.get("n_records_saved"), desc=f"records saved from {src}", unit="records")
    numbers["screen_records_before_dedupe"] = num(int(pd.to_numeric(screening["n_hits"]).sum()),
                                                  desc="records before de-duplication (search + repo list)",
                                                  unit="records")
    numbers["screen_unique_records"] = num(len(screening), desc="unique records screened", unit="records")
    reasons = screening.groupby(["decision", "reason"]).size()
    for (d, r), c in reasons.items():
        numbers[f"screen_{d}_{r.replace('-', '_')}"] = num(int(c), desc=f"screening: {d} ({r})", unit="records")
    # tables
    per_study = []
    for sid, g in prim.groupby("study_id", sort=False):
        per_study.append({"study_id": sid, "year": g["year"].iloc[0], "citation": g["citation"].iloc[0],
                          "n_findings": int(len(g)), "classes": "".join(sorted(set(g["design_class"]))),
                          "effects": ";".join(sorted(set(g["effect_type"]))),
                          "vulnerable": bool(g["vulnerable"].eq("yes").any()),
                          "strict": bool((g["vulnerable"].eq("yes") & g["depends_on_between_contrast"].eq("yes")).any()),
                          "best_tag": vt[sid], "access": g["access"].iloc[0]})
    cls_effect = (prim.pivot_table(index="effect_type", columns="design_class", values="finding_id", aggfunc="count",
                                   fill_value=0).reindex(index=EFFECTS, columns=CLASSES, fill_value=0)
                  .reset_index().to_dict(orient="records"))
    tables = {"studies": per_study, "conflict_groups": conflict_table, "class_by_effect": cls_effect,
              "grey_studies": [{"study_id": s, "classes": "".join(sorted(set(g["design_class"]))),
                                "vulnerable": bool(g["vulnerable"].eq("yes").any())}
                               for s, g in df[df["in_primary"] == "no"].groupby("study_id", sort=False)]}
    extra = {"vulnerable_rule": RULE, "protocol": "lit/audit_protocol.md",
             "classes": {"P": "pooled >= 2 championships, no championship/venue term",
                         "S": "single championship, conclusion generalised",
                         "E": "era/period or other championship-level factor contrast, championships nested in its levels",
                         "M": "championship/venue modelled (M_avg: conclusion averages over venues)",
                         "W": "within-championship comparison only, conclusion restricted", "U": "unclear"},
             "caveat": "Counts classify designs, not the truth of findings; the search is not exhaustive and is "
                       "English-dominant; closed full texts were coded from abstracts or secondary sources."}
    return numbers, tables, extra


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--studies", default="lit/audit_studies.csv")
    ap.add_argument("--screening", default="lit/audit_screening.csv")
    ap.add_argument("--search-log", default="lit/audit_search/search_log.json")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    paths = [ROOT / a.studies, ROOT / a.screening, ROOT / a.search_log]
    df, screening = load(paths[0]), load(paths[1])
    log = json.loads(paths[2].read_text(encoding="utf-8"))
    errs = validate(df, screening)
    if errs:
        raise AuditError("lit audit coding violates the protocol:\n  " + "\n  ".join(errs))
    numbers, tables, extra = compute(df, screening, log)
    out = write_result(ROOT / a.out if not Path(a.out).is_absolute() else a.out, NAME, numbers, paths, mock=False,
                       tables=tables, extra=extra)
    n, k = numbers["n_studies"]["value"], numbers["k_vulnerable_studies"]["value"]
    print(f"wrote {out}: N = {n} studies, K = {k} vulnerable ({100 * k / n:.0f}%); "
          f"findings {numbers['k_vulnerable_findings']['value']}/{numbers['n_findings']['value']}; "
          f"conflict groups {numbers['n_conflict_groups']['value']}")


if __name__ == "__main__":
    main()
