# When each analysis plan was committed, relative to its first result

The abstract calls its tests "pre-specified": each decision rule was written and committed before the quantity it
governs was first computed. The public repository was assembled from the original working history, so its own commit
dates are later; the original commits are listed here (Pacific Daylight Time, UTC-7).

| Plan | Plan committed | First result committed |
|---|---|---|
| `analysis/prereg_systematic.md` (H1-H5, O2) | d6a2b69, 2026-09-30 05:37 | `analysis/outputs/systematic.json`, 4f3c705, 06:23 |
| `analysis/prereg_addendum_trend.md` (H1-S4, H6) | 55a54d5, 2026-09-30 10:59 | `analysis/outputs/trend.json`, ecea033, 11:13 |
| `lit/audit_protocol.md` (literature audit) | bd48da7, 2026-09-30 17:12 | `analysis/outputs/lit_audit.json`, 8ccf666, 17:46 |
| `analysis/prereg_guardband.md` (guard band) | e6203c2, 2026-09-30 17:30 | `analysis/outputs/guardband.json`, c0b9b42, 17:49 |

The data had been explored before these plans were written (the championship offsets were known), so these are
pre-specified analyses of existing data, not a pre-registration with a registry. Deviations are listed in the dated
addenda inside each plan; the recent-championship probe (`probe.*`) was not pre-specified and is labelled exploratory.

## History commitment

The original working repository stays private during anonymous review, because every commit carries the author's
name. Its full history (63 commits from 2026-09-29 to 2026-10-01, ending at commit 12c17e0) is packed in a git bundle
with SHA-256 `f8b06f044c7f970b409df89748cc944a53ac4562203c4579f322c961cef60df5` (55,710,959 bytes). After review the
bundle will be deposited or provided on request, so anyone can check that it matches this hash and that each plan above
was committed before its first result. Publishing the hash fixes the history as of this commit; the times inside it are
the ones git recorded.
