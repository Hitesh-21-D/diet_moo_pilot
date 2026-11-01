# APPO implementation and experimental protocol

## Repository audit and preserved formulation

The dataset is loaded by `src.data_loader.load_indb()`: the observed workbook has
1,014 rows and 82 columns, and cleaning retains 818 rows and eight columns. The
four pools contain 60 meal-specific food choices plus one NONE per meal. The
original profile, pools, serving rules, objective functions and all 33 constraints
are unchanged. Source records use `servings_unit`; decoded records use
`serving_unit`. The initialization test's incorrect key was fixed.

The synthetic pilot is male, 22 years, 178 cm, 57.5 kg, activity factor 1.55,
weight-gain adjustment 300 kcal. Targets from the existing code are energy
2752.88 kcal, protein 103.50 g, carbohydrate 455.34 g, fat 57.50 g, fibre 30 g.
There are 24 real-encoded variables, interpreted as 12 categorical food indices
paired with normalized serving genes. Decoding rounds food indices and maps
portions to each food's practical increments. NONE contributes zero nutrition.

The minimized objectives are nutritional deviation, habit deviation, repetition
penalty and meal-energy-distribution deviation. Constraints comprise nine nutrient
bounds, four duplicate-food checks, eight active-food-count bounds and twelve meal
role checks. Some comments in the old constraints module still describe ten role
checks; the actual implementation correctly returns twelve and 33 overall.
Lunch and dinner require exactly one staple and one protein/curry. No constraints
were relaxed. All APPO evaluation calls invoke the original problem's `_evaluate`.

The original five baseline modules and `run_all_algorithms.py` are preserved.
The standalone `run_moead.py` had a stale `penalty_factor=10.0` constructor argument
that the actual `MOEADDietProblem` does not accept. This argument was removed; the
existing wrapper's penalty equations are unchanged.
MOEA/D retains its existing penalty wrapper; post-search objectives are recomputed
without penalties for every algorithm. The original extraction utility verifies
and deduplicates diets but does not eliminate dominated vectors. The new experiment
pipeline additionally performs non-dominated sorting for **every** algorithm.

## Implemented architecture

`run_appo(problem, config=None, seed=42, verbose=True)` returns `(APPOResult,
runtime_seconds)`. Explicit `seed` controls the run; `config.seed` is the fallback
seed for direct initialization calls. The result exposes X, F, final_positions,
evaluations, history, repair_statistics and the requested history properties.
Empty archives have shape (0,24) and (0,4).

1. **Initialization:** retain the original 30% habit-guided and 70% role-guided
   design. Optional-food sampling now draws from a finite compatible candidate
   list rather than retrying indefinitely when a role is absent. This changes the
   random draw sequence but not the problem. NONE sampling explicitly returns zero
   instead of dividing by its zero serving increment.
2. **Memory:** per-meal maps of original food codes and servings are copied once
   into `RepairContext`. They are never updated with generated diets. They guide
   initialization, habit mutations, structural replacement preferences, substitution
   proposals and repair ties. Shared F2 remains unchanged even in NoMemory.
3. **Repair:** structural correction, discrete portion trials, then same-role food
   substitutions, all bounded by the budget. Search trials are evaluated by the
   centralized gateway. Feasible candidates stop repair immediately.
4. **Variation:** tournament parents, complete six-gene meal exchanges, categorical
   replacements and discrete serving mutations. No polynomial mutation of indices.
5. **Survival:** feasibility-first, then constrained Pareto fronts and diversity.
6. **Archive:** feasible non-dominated practical diets, with capacity 100 and
   iterative objective/decision-space diversity truncation.

## Equations and precise choices

Let G be the original vector of 33 inequalities and F the original four objectives.

`CV(x) = sum_j max(0, G_j(x))`.

APPO requires `all(G <= 0)` for feasibility. This is marginally stricter than the
shared reporting utility's default 1e-12 tolerance; APPO does not label positive
violations feasible.

Feasibility-first comparison prefers a feasible candidate to any infeasible one;
between infeasible candidates lower CV wins. Between feasible candidates, a
dominates b iff every F_i(a) <= F_i(b) and at least one is strictly smaller.
Non-dominated tournament ties are random; survival ties use diversity, not F1.

For adaptation let q be the feasible population fraction, u the unique practical
diet ratio, h the number of consecutive unchanged archive-signature sets, W the
stagnation window (10) and tau the uniqueness threshold (0.15).

```
s = min(h/W, 1)
d = max(0, tau-u) / max(tau, 1e-12)
pm = clip(pm_initial + 0.10*(1-q) + 0.10*d + 0.10*s, 0.05, 0.40)
pc = clip(pc_initial + 0.05*q     - 0.10*d - 0.10*s, 0.65, 0.95)
```

Configured bounds replace the displayed default bounds. pm is per food/quantity
pair; pc is per offspring. Initial rates are pm=0.20, pc=0.90. A crossover event
independently copies each entire meal from the second parent with probability 0.5.
Conditional on mutation, with probability 0.35 the memory branch restores a
same-role baseline food and its encoded portion (an empty slot may receive a
baseline component). Otherwise food versus portion mutation is chosen equiprobably.
Portion mutation draws from practical serving levels. Food mutation uses a distinct
same-role food; an empty slot may introduce any meal-pool food. Duplicates or role
violations can arise and are handled by repair and the unchanged constraints.

Structural repair enumerates the finite role-valid two/three-food combinations
per meal once. Invalid meals choose the combination minimizing set additions/removals,
then maximizing retained baseline foods when memory is enabled. Surviving pairs
retain their original portions. Structural proposals are accepted only if total
CV does not increase; if nutrient damage outweighs structural improvement, the
proposal is rejected and the candidate remains infeasible. The standalone structural
function guarantees meal structure, not nutritional feasibility. Enumeration is
role bookkeeping, not uncounted full candidate scoring.

The first half of up to 20 repair attempts proposes a +/- one-step portion edit.
The second half proposes a nonduplicating same-role substitution. With memory
enabled, half the substitution proposals prefer available familiar foods. Candidate
acceptance is lexicographic on `(CV, practical_interventions, F2, F1)`; without memory
it is `(CV, F1)`. Repair stops immediately on feasibility, preserving feasible
portions rather than doing further local optimization. It does not replace Pareto
survival with a scalar objective. Structural fixes are separately diagnosed;
substitution and serving counters count accepted nutritional repair operations.

Practical uniqueness uses the original `diet_signature`: meal-wise sorted food and
portion pairs ignoring NONE. Slot permutations and equivalent serving genes are
duplicates. Archive updates combine previous archive and accepted candidates,
deduplicate, discard infeasible/dominated points and repeatedly delete the lowest
diversity score until the capacity is met.

Objective crowding is the existing NSGA-II-style crowding function, normalized by
the largest finite score; boundary infinities receive score 1. A dietary vector has
one coordinate per `(meal, food_code)` in the compared set, with missing foods zero
and amounts normalized by that coordinate's maximum observed amount. For n diets:

```
D(i,j) = mean_k |v_ik - v_jk|
z_i = min_{j != i} D(i,j)
decision_i = z_i / max(max_j z_j, 1e-12)
score_i = (1-w)*normalized_crowding_i + w*decision_i; default w=0.30
```

Both components are bounded [0,1]. Distances account for food presence and portions
and are invariant to slot order. Normalization is local to the current front, not
fixed across time. Boundary objective values are favored but not guaranteed
preservation under dual-space truncation. Ties delete the earliest tied entry,
deterministically. NoDualDiversity sets w=0 in archive and population survival.

## Evaluation accounting and pseudocode

Every search-time full candidate assessment goes through `EvaluationBudget`.
Objectives and all constraints in one pass cost one evaluation, including repeated
and rejected trials. The gateway disallows budget overflow and validates shapes
and finite values. Cached evaluated candidates require no reassessment during
selection/archive maintenance. Metadata, signature generation, role enumeration
and intervention counting do not evaluate nutritional objectives or constraints.

```
initialize RNG, immutable memory, food metadata and budget
initialize min(population_size, budget) candidates; evaluate all
for each initial candidate: perform bounded repair while budget remains
build feasible unique Pareto archive; record initial diagnostics
while budget remains:
    measure feasibility, uniqueness and archive stagnation; compute pc, pm
    for up to population_size children while budget remains:
        tournament-select two parents
        exchange whole meals; mutate foods/portions using stable memory
        evaluate child; perform counted bounded repair
    update feasible unique archive from accepted children
    apply feasibility-first elitist survival to parents plus children
    record evaluation count, feasibility, uniqueness, CV, pc, pm and archive size
return archive, population, diagnostics and actual evaluations
```

At small budgets, initial repair may consume all remaining evaluations before any
evolutionary generation. This is explicitly visible as generation=0 in history.
Unrepaired initial members still have valid evaluated records. Runtime includes
metadata construction and initialization.

## Experimental runners and outputs

Run from the repository using `.venv/Scripts/python.exe`:

```
python test_appo_initialization.py
python test_problem.py
python -m unittest test_appo -v
python run_appo.py --budget 15000 --seed 42
python run_all_algorithms_with_appo.py --budget 15000 --seed 42
python run_repeated_experiments.py --smoke
python run_repeated_experiments.py --smoke --ablation
python run_repeated_experiments.py --seeds 0 1 2 --budget 15000
python run_repeated_experiments.py
python run_repeated_experiments.py --ablation
python run_repeated_experiments.py --repair-comparison --seeds 42 43 44 --budget 15000
```

Default repeated runs use 30 independent seeds (0-29); smoke uses 42,43,44 at 1,000
evaluations. Explicit seeds and budget override defaults. Five ablation settings:
Full, NoMemory, NoRepair, NoAdaptation, NoDualDiversity. NoRepair bypasses every
repair stage; NoMemory disables all added baseline guidance (not shared F2);
NoAdaptation fixes pc/pm; NoDualDiversity removes decision-space ranking but retains
practical deduplication as a validity requirement.

All executions create timestamped UTC directories under `outputs/experiments`.
Historical outputs are preserved. Manifests record package versions, dataset hash,
profile, seeds, configurations and counting/timing policies. Raw NPZ files preserve
chromosomes, objectives and final populations. CSVs hold history, repairs, archive,
representative diets, metrics, reference front and normalization bounds. PNG charts
have evaluation counts on convergence axes; repeated comparison error bars are
sample standard deviations, not confidence intervals. Empty-front indicators are
explicitly missing/infinite rather than fabricated zero deviations.

The comparative runner uses whole generations at or below the requested budget:
NSGA-II/III/SPEA2 use floor(B/100) generations; MOPSO uses floor(B/100)-1 iterations
plus its initial population; MOEA/D uses floor(B/84) generations. At B=15000 expected
counts are 15000,15000,14952,15000,15000,15000 respectively, verified against returned
counters. Thus budgets are approximately, not exactly, equal. The old MOPSO setting
was 15100; the old MOEA/D 180-generation setting was 15120. Baseline algorithms
themselves are not modified. External wall-clock timing includes initialization for
all algorithms (the old MOPSO internal timer excludes it).

Post-search feasibility and objective verification is separate reporting work,
excluded from search budgets for all algorithms, and never fed back into search.
One reference front is formed from all feasible non-dominated fronts across every
algorithm **and every seed** in an experiment. Common ideal/nadir bounds use their
union; HV uses normalized reference point (1.1,1.1,1.1,1.1). IGD, spacing, intervention
counts and `PETQ=HV/(IGD*ln(1+T))` reuse the original metrics and numerical safeguards.
No metric, including PETQ, guides APPO. Single-algorithm output intentionally does
not report self-referential HV/IGD/PETQ as comparative evidence.

Repeated summaries include mean, sample SD and finite count. Empty archives and
excluded statistical pairs are reported. Paired two-sided Wilcoxon tests compare
APPO with each comparator; Holm correction applies to the entire reported family
of metrics and comparators. Rank-biserial effects use APPO-minus-comparator signed
differences; positive favors APPO only for higher-is-better metrics. Fewer than three
valid pairs produce no p-value. Three-seed smoke tests are engineering checks, not
evidence of general superiority. No final comparison results were used for tuning.

## Complexity, novelty and limitations

With P population, A archive capacity, M=4 objectives, E evaluated candidates and
R bounded repair trials, full evaluations cost O(E*C_eval). Each generation uses
approximately O(M*P^2) non-dominated sorting and O(P^2*K) dietary distances for K
meal-food coordinates. Iterative archive truncation can cost O((P+A)^3*K) in the
worst case; capacities are small in this pilot. Precomputing meal combinations is
O(sum_m C(food_count_m,3)), and invalid meal repair scans these combinations.
Repair's extra evaluations are included in E; it reduces generations achievable
at a fixed budget and can increase wall-clock work through proposal bookkeeping.

Deb-style comparisons, Pareto sorting, crowding, archives, knowledge-based seeding,
local repair and adaptive variation are established techniques. APPO's proposed
contribution is their specific integration with stable Indian-diet habit memory,
meal/portion-aware proposals, budget-accounted personalized repair and dual-space
diversity. This is an engineering/research proposal, not a claim that its component
techniques are newly invented. No literature-priority claim or invented citation
is made; a systematic literature review remains necessary.

This is one synthetic pilot profile and a restricted food pool, not clinical
validation. INDB composition estimates and serving assumptions may not reflect a
particular kitchen, person or recipe. Constraint feasibility means compliance with
the encoded model, not nutritional or medical suitability for real users. Habit
preservation can conflict with feasibility. Repair is stochastic, greedy and bounded
and may fail; archive diversity may discard objective extremes. The synthetic
profile, fixed seeds and empirical reference front limit generalizability. A common
empirical front is relative to observed outputs, not a known global Pareto front.
Full multi-seed, multi-profile sensitivity studies, independent validation and
appropriately reviewed user studies are needed before strong publication claims.

See `APPO_VERIFICATION_REPORT.md` for executed checks and measured outcomes. A
runner being present is not evidence that its long experiments have completed.

The `--repair-comparison` mode runs only APPO and APPO-NoRepair with identical
settings except `repair_enabled`. It alternates execution order between seeds and
retains a source snapshot and SHA-256 hashes in each experiment folder. Runs execute
sequentially. For the initial full-budget development comparison, seeds 42,43,44
were selected in advance and Python was launched with `PYTHONHASHSEED=0`. This is
not a held-out evaluation or a replacement for the 30-seed study. Use
`python summarize_repair_comparison.py <experiment-directory>` to independently
check saved objectives, all constraints, front uniqueness/non-dominance, final
population feasibility and exact repair budget accounting, and write `REPORT.md`.

For bitwise cross-process reproducibility, set `PYTHONHASHSEED=0` before starting
Python as well as passing the NumPy seed. The unchanged shared habit objective
iterates Python sets, so floating-point summation order can vary slightly across
processes with randomized hash seeds. The regression suite verifies identical
APPO runs in one process. The delivered development runs did not pin the hash seed;
their raw chromosomes and verified objective values are retained for exact audit.

`run_all_algorithms_with_appo.py --reuse-from <folder> [<folder> ...]` can reuse
completed raw runs with matching profile, workbook hash, budget and seed. It writes
a fresh directory and records source directories; it never overwrites the source.
This is useful after a late failure or when recomputing a common empirical front.
