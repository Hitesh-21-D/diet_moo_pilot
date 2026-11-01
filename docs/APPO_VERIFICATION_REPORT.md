# APPO implementation verification — 31 October 2026

## Status and experiment provenance

The integrated optimizer, standalone runner, six-algorithm comparison, ablation
switches, repeated-experiment runner, CSV exports, charts and technical documentation
are implemented and exercised. The original objectives, 33 constraints, profile,
food pools, serving rules and five baseline algorithms are unchanged.

The full APPO pilot used seed 42 and exactly 15,000 counted evaluations. The
six-algorithm comparison combines the five completed baseline searches with this
corrected APPO run. The first comparison process had already imported the old
NONE-serving sampler before its fix and failed when it eventually reached APPO.
Its completed baseline raw results were retained. The successful comparison used
`--reuse-from`, verified matching inputs, recomputed shared objective values, and
built a new 227-point empirical reference front. No historical pilot scores were
hardcoded and no algorithm was tuned from the comparison results.

Authoritative output directories under `outputs/experiments/`:

| Experiment | Directory | Executed scope |
|---|---|---|
| Standalone full APPO | `20261031T044745408735Z_appo` | Seed 42, 15,000 evaluations |
| Six-algorithm comparison | `20261031T045453134436Z_six_algorithms` | All six, approximately 15,000 each |
| Repeated smoke | `20261031T045111479626Z_repeated` | Six algorithms x seeds 42,43,44, budget 1,000 |
| Ablation smoke | `20261031T044844260811Z_ablation` | Five variants x seeds 42,43,44, budget 1,000 |
| Larger ablation smoke | `20261031T045435989696Z_ablation` | Five variants, seed 42, budget 3,000 |

Earlier diagnostic/failed run directories are retained for transparency, not used
as completed experiments. Logs are preserved under `outputs/verification/`.

## Files created or modified

Created:

| File | Purpose |
|---|---|
| `.gitignore` | Exclude virtual environments and generated Python bytecode |
| `src/algorithms/appo_budget.py` | Candidate records and centralized strict evaluation accounting |
| `src/algorithms/appo_repair.py` | Stable memory, structural correction and bounded nutritional repair |
| `src/algorithms/appo_operators.py` | Meal crossover, categorical/portion/habit mutation, rate equations |
| `src/algorithms/appo_selection.py` | Feasibility-first tournament/survival and dual-space diversity |
| `src/algorithms/appo_archive.py` | Feasible non-dominated archive with practical deduplication |
| `src/algorithms/appo.py` | Integrated optimizer, result object and histories |
| `src/appo_experiments.py` | Shared experiment execution, verification, metrics and exports |
| `run_appo.py` | Standalone APPO CLI and representative diet output |
| `run_all_algorithms_with_appo.py` | Six-algorithm CLI, common front and safe raw-run reuse |
| `run_repeated_experiments.py` | Multi-seed/ablation CLI, summary statistics and paired tests |
| `test_appo.py` | Eight focused regression tests |
| `test_appo_results.py` | Independent saved full-run validation |
| `docs/APPO_TECHNICAL_DOCUMENTATION.md` | Architecture, equations, pseudocode, protocol and limitations |
| `docs/APPO_VERIFICATION_REPORT.md` | This measured results and verification record |

Modified:

| File | Change |
|---|---|
| `src/algorithms/appo_config.py` | Ablation switches and parameter validation |
| `src/algorithms/appo_initialization.py` | NoMemory support, bounded optional-role sampling, NONE sampler fix |
| `test_appo_initialization.py` | Correct decoded field to `serving_unit` |
| `run_moead.py` | Remove stale unsupported `penalty_factor` constructor argument; optimizer unchanged |

Generated experiment files include `manifest.json`, `raw/*.npz`, representative
diet CSVs, history/repair/archive/configuration files, metrics CSVs, reference-front
CSV, normalization JSON, summary/statistics CSVs and PNG figures. The six-algorithm
directory also records reuse sources. Existing baseline result files were preserved.

## Architecture delivered

APPO integrates 30/70 habit/role-guided initialization, immutable original-diet
memory, bounded structural/portion/same-role repair, adaptive meal-aware variation,
feasibility-first Pareto survival and a practical-diet archive. The four objectives
remain separate Pareto criteria. PETQ is reporting-only. Repair candidates,
including rejected trials, consume the same budget as initial/offspring assessments.
Archive maintenance reuses stored evaluations and combines normalized objective
crowding with normalized nearest-neighbor dietary distance at weight 0.30.

The full pilot became 100% population-feasible at 10,336 evaluations. Mutation
probabilities varied during the run (roughly 0.20–0.309); crossover varied roughly
0.8905–0.95. The exported histories give exact rates and counted evaluations.

## Checks executed

- `test_problem.py`: completed successfully, confirming the actual 24/4/33 API.
- `test_appo_initialization.py`: passed; 100/100 structurally valid, 0/100 initially
  nutritionally feasible, 99 practical unique diets. Mean retained foods were 8.17
  for habit initialization and 1.94 for role initialization after bounded sampling.
- `python -m unittest test_appo -v`: **8 tests passed**. Coverage includes structure,
  bounds/quantization, invalid/NONE genes, deterministic initialization and complete
  runs, budget exhaustion, repair nonworsening, feasibility-first comparison,
  non-dominated deduplicated archive, mixed operators, memory/repair/adaptation
  switches, NoDualDiversity in both survival and archive, and representative labels.
- Full standalone saved-artifact validation: passed. All 57 diets independently
  satisfy all 33 constraints, match the original four objectives, are mutually
  non-dominated, and have unique practical signatures. The three categories exist.
- Full six-algorithm saved APPO validation: passed the same independent checks.
- Budget audit: initial/offspring records plus all repair trial evaluations sum
  exactly to 15,000. No search-time evaluations exceeded the cap.
- Six-algorithm runner with completed-run reuse: exited successfully and generated
  the comparison, 227-point reference front, normalization and representative diets.
- Repeated smoke: all 18 runs completed, including common-reference scoring,
  summaries, paired test output and variability plots.
- Ablations: all 15 three-seed smoke runs and five 3,000-budget runs completed.
- Syntax parsing: all 42 Python source files parsed successfully.
- Diff whitespace check passed. Feasibility and algorithm comparison PNGs were
  visually inspected and were readable.

Initial tests/full attempt failed on division by zero when sampling NONE; this was
fixed and the relevant tests/full APPO rerun passed. There are no outstanding test
failures in the final implementation. The 30-seed full-budget and full-budget
ablation campaigns have **not** been run. The old standalone `run_moead.py` was not
rerun end-to-end; its shared algorithm was executed successfully by the new runner.

## Full six-algorithm results

All rows use the same rebuilt reference front, normalization, HV reference and
metric formulas. Feasibility is the final population fraction, not archive fraction.

| Algorithm | Unique feasible diets | HV | IGD | Spacing | Feasibility | PETQ |
|---|---:|---:|---:|---:|---:|---:|
| NSGA-II | 95 | 0.643353 | 0.152075 | 0.049695 | 100% | 1.454606 |
| NSGA-III | 17 | 0.419330 | 0.332986 | 0.033799 | 100% | 0.420780 |
| MOEA/D | 27 | 0.472315 | 0.340985 | 0.037065 | 100% | 0.539431 |
| SPEA2 | 100 | 0.767952 | 0.089908 | 0.023792 | 100% | 2.972438 |
| MOPSO | 92 | 0.527318 | 0.192356 | 0.030500 | 10% | 0.943749 |
| APPO | 57 | 0.686519 | 0.153920 | 0.087800 | 100% | 1.639287 |

| Algorithm | Mean nutrition deviation | Mean habit deviation | Mean interventions | Runtime (s) | Evaluations |
|---|---:|---:|---:|---:|---:|
| NSGA-II | 0.119569 | 0.744480 | 17.326316 | 48.812545 | 15,000 |
| NSGA-III | 0.161172 | 0.761479 | 18.941176 | 95.236620 | 15,000 |
| MOEA/D | 0.118820 | 0.538200 | 12.037037 | 132.581784 | 14,952 |
| SPEA2 | 0.101349 | 0.724274 | 16.700000 | 134.691932 | 15,000 |
| MOPSO | 0.072908 | 0.747393 | 17.260870 | 80.402649 | 15,000 |
| APPO | 0.127938 | 0.680416 | 14.192982 | 167.071771 | 15,000 |

SPEA2 had the best HV, IGD, spacing and PETQ. APPO ranked second for HV and PETQ,
but had the worst spacing and the longest observed runtime. MOEA/D had the lowest
habit deviation and fewest interventions; MOPSO had the lowest mean nutrition
deviation but only 10% final-swarm feasibility. NSGA-II had the shortest measured
runtime. Number of Pareto diets alone is not a superiority criterion.

These timings include initialization but were collected while development runs
overlapped on the same machine. They are measured development timings, not a
controlled publication-grade runtime comparison. The slight MOEA/D budget shortfall
is explicit; this is approximately budget-matched, not exactly equal.

## APPO representative diets

Food names below are shortened only for readability; source names, codes, serving
units, totals and objectives are retained in the CSV. These are model outputs for
the synthetic pilot, not clinically validated prescriptions.

### Best Nutritional Match

- Breakfast: 3 boiled eggs; 3 idli.
- Lunch: 2 plates boiled rice; 0.5 bowl mixed vegetable salad with curd sauce;
  0.75 bowl palak paneer.
- Snack: 2 bowls rice flakes; 1 tall glass salted lassi.
- Dinner: 2 plates boiled rice; 0.25 bowl matar paneer; 0.25 bowl mixed vegetable
  salad with curd sauce.

Totals: **2783.11 kcal, 101.00 g protein, 452.41 g carbohydrate, 59.80 g fat,
31.98 g fibre**. F1–F4: **(0.029489, 0.765625, 0.200000, 0.070561)**.
Practical interventions: **14**.

### Minimum Dietary Change

- Breakfast: 1 tea cup hot tea; 2 boiled eggs; 3 idli.
- Lunch: 1 bowl sambar; 1 bowl mixed vegetable salad with curd sauce; 2 plates rice.
- Snack: 1.25 bowls vegetable poha; 1 tea cup hot tea.
- Dinner: 1 bowl matar paneer; 1.75 plates rice; 1 bowl cucumber raita.

Totals: **2690.86 kcal, 95.98 g protein, 425.89 g carbohydrate, 62.77 g fat,
48.37 g fibre**. F1–F4: **(0.172798, 0.495833, 0.181818, 0.101687)**.
Practical interventions: **10**.

### Balanced Compromise

- Breakfast: 3 boiled eggs; 3 idli; 1 egg serving scrambled egg.
- Lunch: 2 plates rice; 1 bowl sambar.
- Snack: 1 bowl vegetable poha; 1 tall glass sweet lassi.
- Dinner: 1.5 bowls washed moong dal; 2 plates rice; 0.25 bowl vegetable curry
  with coconut.

Totals: **2692.97 kcal, 94.81 g protein, 439.57 g carbohydrate, 58.24 g fat,
38.07 g fibre**. F1–F4: **(0.084496, 0.662500, 0.100000, 0.060295)**.
Practical interventions: **13**.

## Ablation findings

At 1,000 evaluations for seeds 42,43,44, full APPO had no feasible archive in any
seed. NoRepair found 1,0,6 feasible diets respectively. The other variants found
none. Initial repair consumed the remaining budget before full APPO began
evolution; this smoke test cannot assess the benefit of adaptation or dual-space
survival at a mature search stage.

The 3,000-evaluation, seed-42 ablation uses its own common reference across all five
variants; these metric values must not be compared numerically to the 15,000-budget
six-algorithm table, which has different normalization/reference data.

| Variant | Feasible Pareto diets | Final feasibility | HV | IGD | Mean interventions | PETQ |
|---|---:|---:|---:|---:|---:|---:|
| Full APPO | 1 | 1% | 0.064934 | 0.814531 | 17.00 | 0.027581 |
| NoMemory | 2 | 2% | 0.078490 | 0.566844 | 18.00 | 0.047027 |
| NoRepair | 56 | 100% | 0.664737 | 0.007352 | 13.59 | 33.732272 |
| NoAdaptation | 5 | 7% | 0.181228 | 0.552833 | 17.40 | 0.112561 |
| NoDualDiversity | 1 | 1% | 0.064934 | 0.814531 | 17.00 | 0.027581 |

The observed evidence does **not** establish that all added mechanisms improve
performance. Repair is expensive under these small budgets; disabling it performed
better. NoAdaptation also outperformed full APPO in this small single-seed check.
NoDualDiversity matched full APPO while the archive was tiny. NoMemory traded a
slightly larger feasible set for more interventions. Full-budget, paired multi-seed
ablations are required to assess each mechanism reliably. No statistical significance
or population-level superiority claim is supported by these checks.

## Research assessment and remaining work

APPO is an operational constrained, personalized multi-objective optimizer with
auditable budget accounting and feasible full-pilot outputs. It shows a useful
single-seed trade-off between objective coverage and habit preservation relative to
some baselines, but SPEA2 remains stronger on several Pareto metrics and MOEA/D on
habit preservation. The proposed novelty is the specific integration of established
methods with meal/portion semantics and stable habit memory, not invention of
Pareto sorting, crowding, repair or adaptive variation themselves.

Before journal-level claims: run 20–30 full-budget paired seeds, full-budget
ablations, controlled sequential timing, multiple profiles/food-pool sensitivities,
cross-process reproducibility checks with pinned Python hash seed, and an appropriate
literature review and independent validation. The shipped runner defaults to 30
seeds and supports Wilcoxon tests, rank-biserial effects and Holm correction. That
capability is implemented; the long campaigns remain unexecuted.
