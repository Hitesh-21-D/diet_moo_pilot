# Final flexible-v2 verification

Source SHA-256: `c05e24ddd0566c49500f3a3220acbcfd1f98c99528959fd9fd770b514791a4a5`

| Pattern | Algorithm | Evaluations | Feasible Pareto diets |
| --- | --- | ---: | ---: |
| one-meal | NSGA-II | 15000 | 18 |
| one-meal | NSGA-III | 15000 | 5 |
| one-meal | MOEA/D | 14952 | 4 |
| one-meal | SPEA2 | 15000 | 11 |
| one-meal | MOPSO | 15000 | 0 |
| one-meal | APPO | 15000 | 8 |
| five-meals | NSGA-II | 15000 | 83 |
| five-meals | NSGA-III | 15000 | 19 |
| five-meals | MOEA/D | 14952 | 15 |
| five-meals | SPEA2 | 15000 | 94 |
| five-meals | MOPSO | 15000 | 0 |
| five-meals | APPO | 15000 | 11 |

These are seed-42 functional checks, not a repeated-seed superiority study.
MOPSO completed its budget but returned no feasible diets. Every returned diet
was independently checked against the versioned constraints and its objectives recomputed.

14 backend tests, 8 legacy APPO regression tests, 6 frontend tests, and the production build passed.
Browser checks confirmed full-catalogue search, pagination, custom-meal persistence,
equal-height meal cards, and complete current/suggested meal columns without console errors.

## Live PostgreSQL application checks

Seven full-budget jobs passed queue, snapshot, independent-constraint,
evaluation-accounting and CSV/JSON export checks. Each input day has its own results.

| Input day | Algorithm | Status | Feasible diets |
| --- | --- | --- | ---: |
| Day 1 | APPO | completed | 17 |
| Day 1 | MOEA/D | completed | 8 |
| Day 1 | MOPSO | no_feasible | 0 |
| Day 1 | NSGA-II | completed | 92 |
| Day 1 | NSGA-III | completed | 18 |
| Day 1 | SPEA2 | completed | 51 |
| Day 2 | APPO | completed | 23 |
