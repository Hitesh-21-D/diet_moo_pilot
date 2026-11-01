# Questionnaire cohort benchmark — terminal workflow

No frontend or PostgreSQL is required. All processing and files stay local.
The supplied export is already imported: **174 registered, 93 ready, 81 blocked**.
Eligibility is not a claim that these participants have already been benchmarked.
The agreed protocol ignores dietary restrictions/avoidances (clearly labelled),
uses 300 kcal for gain/loss and zero for maintenance, and retains flexible-v2.

## Run and resume

Open PowerShell in `C:\Users\Hitesh\Desktop\diet_moo_pilot`:

```powershell
.\.venv\Scripts\python.exe -B run_survey_benchmark.py run --batch full-budget
```

This runs all six algorithms on every eligible respondent at 15,000 requested
evaluations, seed 42. Completed identical jobs are skipped automatically. Ctrl+C
stops the current job; repeat the same command to resume. Keep the terminal open
and the laptop awake during a run. One sequential worker uses one numerical thread.
There are 558 jobs for 93 eligible participants at one seed, or 1,044 if all 174
become eligible. Multiple seeds multiply those counts. Progress includes an ETA.

```powershell
# Run the next 12 pending jobs and stop cleanly
.\.venv\Scripts\python.exe -B run_survey_benchmark.py run --batch full-budget --max-jobs 12

# A separate repeated-seed research batch
.\.venv\Scripts\python.exe -B run_survey_benchmark.py run --batch repeated-3 --seeds 42 43 44

# Quick development check; never mix this with full-budget results
.\.venv\Scripts\python.exe -B run_survey_benchmark.py run --batch smoke --budget 1000 --limit-participants 1

.\.venv\Scripts\python.exe -B run_survey_benchmark.py status
.\.venv\Scripts\python.exe -B run_survey_benchmark.py summarize --batch full-budget
```

Failed jobs have adjacent logs. Resolve the cause and add `--retry-failed` to the
run command. The default per-job timeout is 1,800 seconds (`--timeout SECONDS`).
The source, workbook, environment, budget, seeds and import-policy settings are
frozen per named batch. A changed protocol requires a new `--batch` name.

## Add respondents

```powershell
.\.venv\Scripts\python.exe -B run_survey_benchmark.py import --export "C:\path\to\new\export"
.\.venv\Scripts\python.exe -B run_survey_benchmark.py run --batch full-budget
```

The export directory must contain participants.csv, food_logs.csv, custom_foods.csv
and export_errors.csv. Stable `response_id` values identify repeat respondents.
Importing identical responses is idempotent. New people are appended; absent people
are retained. Corrected profiles/diets create new case versions and fresh runs.
Old raw checkpoints remain, but reports use the current active case only.
Keep your original export folders: source hashes and normalized cases are recorded,
but original CSV files are never modified or uploaded.

## Audit and corrections

Audit files live in `.local/survey-benchmark/audit`: participants.csv, issues.csv,
food_review.csv, summary.json and corrections.template.json. They account for all
174 participants, including blocked records. Counts overlap: 25 unusable activity
answers, two ages entered as 2007, four heights outside the supported range, 29
people without food logs, 33 custom entries, and 23 coded entries outside the
admitted catalogue. Other incomplete meals are explicitly reported.

Custom foods appear in both food_logs and custom_foods; the latter is treated as
detail metadata, never as additional food. Missing nutrients, activity and ages
are not guessed. Whole participants with unresolved entries are blocked rather
than silently optimizing a truncated diet. Food-label similarity is not enough
to establish a serving/nutrient equivalence.

Copy the correction template to your own corrections.json; retain only reviewed
entries. Use exact response IDs and `meal:entry_index` keys from the audit:

```json
{
  "actual-response-id": {
    "reason": "Participant confirmed age and activity in follow-up",
    "profile": {"age": 19, "activity_factor": 1.55},
    "entries": {
      "breakfast:0": {
        "reason": "Participant confirmed two idli in idli serving units",
        "foods": [{"food_code": "ASC144", "servings": 2}]
      }
    }
  }
}
```

Each correction needs a source/reason; each food mapping needs its own rationale
including unit conversion. A verified mixed-dish entry can map to several foods
with verified quantities. `replace_logs` can supply a confirmed complete list of
rows with meal, meal_index, entry_index, food_code, food_name, quantity,
serving_unit and source. Meal IDs/indexes must match the original meal order.
Skipped-meal conflicts require `skip_policy: "recorded-foods"` or `"skip-meals"`.
Invalid meal-order metadata/export errors must be fixed in a reviewed copy of the
export; retain the original archive. Do not invent meals for empty respondents.

```powershell
.\.venv\Scripts\python.exe -B run_survey_benchmark.py import --export "C:\path\to\export" --corrections "C:\path\to\corrections.json"
.\.venv\Scripts\python.exe -B run_survey_benchmark.py run --batch full-budget
```

Import defaults follow the agreed 300 kcal/unmodelled-restrictions protocol.
`--calorie-adjustment` and `--restriction-policy` make deviations explicit.
The alternative restriction policy `exclude` blocks affected people; it does not
implement allergy classification. Adult assent=False is not treated as refusal;
age and consent metadata are checked separately. Repeated foods in one meal are
combined; numeric meal prefixes preserve identity when display labels repeat.

## Reports and scientific interpretation

For the full-budget batch, open
`.local/survey-benchmark/batches/full-budget/reports`:

| File | Contents |
| --- | --- |
| coverage.csv, summary.json | All participants, eligibility, failed/missing jobs and partial status |
| per_run_metrics.csv | Algorithm × participant × seed metrics for complete comparison cohorts |
| per_participant_metrics.csv | Seed means and within-participant ranks |
| aggregate_metrics.csv | Equal-participant mean, SD, median and valid count per metric |
| paired_statistics.csv | APPO paired comparisons, Wilcoxon, Holm correction, rank-biserial effects |
| references/*.json | Within-participant reference fronts and normalization |

Each checkpoint retains objective/chromosome archives, representative diets,
formulation metadata, actual evaluations, feasibility and runtime. Every returned
solution is independently validated. `failed` means an execution problem;
`no_feasible` means a completed search with no feasible diet. MOEA/D uses 14,952
evaluations at the requested 15,000, following existing generation accounting.

Only respondents with ALL six algorithms and ALL requested seeds finished enter
comparative aggregates. Failed/incomplete/blocked cases stay visible in coverage.
Fronts from different people are never pooled. All algorithms/seeds for one person
share that person's empirical reference front and normalization. Adding people
does not change another person's reference front.

Success rate and mean within-participant HV rank are the primary cohort views
(higher success, lower rank are better). Macro HV/IGD are descriptive averages
of participant-relative scores, not a global-front indicator. Seeds are averaged
first, then participants receive equal weight. Runtime covers shared algorithm
initialization/search, excluding process startup/import/reporting. Concurrent
workloads affect timings.

No-feasible runs have Success=0 and HV/PETQ=0; IGD, spacing and diet deviations
are missing. Their conditional means must be read alongside valid counts and
success coverage. Paired tests use participants, not participant-seed pairs, as
the sampling units. The inherited PairedSeeds/ExcludedSeeds column names in the
shared statistical routine therefore count participants in this report. Single
seed results do not establish robustness to randomness or universal superiority.

All respondent-level files are under git-ignored `.local`. Pseudonymous IDs remain
linkable, not guaranteed anonymous. Do not publish that folder wholesale. These
outputs deliberately ignore preferences/avoidances and should not be delivered
to respondents as restriction-aware dietary recommendations.

## Verification

`python -B -m pytest tests_batch -q` tests append/idempotence, profile validation,
custom-food deduplication and explicit correction, restriction-policy handling,
complete-cohort aggregation, no-feasible conventions, resume and protocol guards.
Actual six-algorithm full-budget validation checkpoints on an imported respondent
are retained in the local full-budget batch and are reused by subsequent runs.

Verified on 1 November 2026: six batch tests passed. One actual questionnaire
respondent completed all six full-budget jobs (89,952 evaluations in total).
Four algorithms produced feasible diets; MOEA/D and MOPSO returned no_feasible.
A second invocation scheduled zero jobs and preserved all six checkpoint mtimes.
The current aggregate is therefore a validation result for one respondent, not
a completed 174-person study. The full-budget command continues the remaining
552 jobs for the other 92 currently eligible respondents.
