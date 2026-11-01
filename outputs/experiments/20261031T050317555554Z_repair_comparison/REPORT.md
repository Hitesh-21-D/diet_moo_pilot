# Full-budget APPO repair comparison

Seeds: [42, 43, 44]. Each run used exactly 15,000 evaluations.

Only repair_enabled differs between variants. Original objectives, constraints, initialization, memory, adaptation and diversity settings are preserved. All runs passed independent checks of budget accounting, original objective values, all 33 constraints, practical uniqueness and Pareto non-dominance. Final population feasibility was recomputed.

Metrics use one empirical reference front and one normalization across all paired runs. Their numerical values are not directly comparable with previous experiments using other fronts.

| Metric | APPO mean ± sample SD | NoRepair mean ± sample SD |
|---|---:|---:|
| UniqueFeasibleDiets | 60.333333 ± 3.055050 | 100.000000 ± 0.000000 |
| HV | 0.612465 ± 0.018999 | 0.973607 ± 0.047692 |
| IGD | 0.247082 ± 0.018102 | 0.079791 ± 0.017012 |
| Spacing | 0.063395 ± 0.013960 | 0.048241 ± 0.009155 |
| PETQ | 0.916963 ± 0.102567 | 4.716286 ± 1.181848 |
| Feasibility | 1.000000 ± 0.000000 | 1.000000 ± 0.000000 |
| MeanNutritionDeviation | 0.145418 ± 0.015362 | 0.102088 ± 0.016773 |
| MeanHabitDeviation | 0.656794 ± 0.025355 | 0.602324 ± 0.049351 |
| MeanInterventions | 14.179862 ± 0.744817 | 13.673333 ± 0.804135 |
| Runtime | 77.357281 ± 2.280049 | 82.380730 ± 1.372603 |
| Evaluations | 15000.000000 ± 0.000000 | 15000.000000 ± 0.000000 |

## Paired seed outcomes

| Seed | APPO HV | NoRepair HV | APPO PETQ | NoRepair PETQ |
|---|---:|---:|---:|---:|
| 42 | 0.627857 | 0.996313 | 1.008364 | 5.609328 |
| 43 | 0.618307 | 0.918804 | 0.936488 | 3.376109 |
| 44 | 0.591231 | 1.005702 | 0.806038 | 5.163421 |

## Repair cost

- APPO: mean repair budget share 92.8%; mean completed generations 10.3.
- APPO-NoRepair: mean repair budget share 0.0%; mean completed generations 149.0.

## Interpretation limits

This is a development comparison, not a held-out test against the five baseline algorithms. Development seeds can identify a direction for further work but cannot establish general superiority. See paired_statistics.csv for two-sided Wilcoxon tests, rank-biserial effects and Holm-adjusted p-values. Positive effects represent APPO minus NoRepair and favor APPO only for higher-is-better metrics. Any modified optimizer still needs an independent full-budget benchmark with 20–30 seeds.

## Measured conclusion

NoRepair changed mean HV by +59.0% and reduced mean IGD by 67.7% relative to current APPO. These are within-experiment comparisons, not comparisons with the earlier five baselines. These indicators favor investigating disabled or selectively scheduled repair.

The HV paired Wilcoxon p-value is 0.2500, Holm-adjusted 1.0000. The HV result does not establish statistical significance at the 0.05 level.
