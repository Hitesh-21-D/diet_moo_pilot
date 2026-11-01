# AmritAHARA flexible-v2

Implemented 31 October 2026. New web experiments use this formulation. The
historical CLI pilot and completed experiment snapshots are retained unchanged.
Do not merge pilot results with flexible-v2 benchmark results.

## Workbook coverage

`data/INDB.xlsx`, sheet `Nutrient Data`, contains 1,014 rows. **818 rows** are
usable under the existing serving-data quality policy, and every one is exposed
in every meal's food search and in all six algorithms' search spaces.

196 rows are excluded: 82 lack serving units and complete serving nutrients;
15 lack serving units; 99 exceed at least one existing serving plausibility
threshold. These are exclusions pending source review, not claims that the foods
themselves are unsuitable. No missing nutrient values are imputed or silently
replaced with zero. The workbook is not modified.

- `catalog/indb-audit.csv`: every source row, Excel row number, inclusion and reason.
- `catalog/food-rules.json`: every admitted food's nutrients, unit, portion rule and rule basis.
- Required fields: unique non-reserved code, name, serving unit and finite
  nonnegative energy/protein/carbohydrate/fat/fibre; energy must be positive.
- Retained screening limits per source serving: 1,500 kcal, 100 g protein,
  200 g carbohydrate, 100 g fat, 50 g fibre. Outliers need source correction;
  they must not be made usable merely by scaling suspicious values down.

## Portions and composition

Explicit rules exist for all 818 foods. Original food-specific overrides remain.
Other countable egg/idli/biscuit/cookie/piece/chapati/roti records use 1–3 whole
units; spoons and ordinary natural serving units use 0.25–2 in 0.25 increments.
Jars and boxes use 0.05–0.25 in 0.05 increments. Whole cakes/pies/flans,
family-sized casserole/souffle/shallow dishes and whole chicken/fish/joints use
0.125–0.5 in 0.125 increments. Chutney/pickle records measured in bowls or plates
also use 0.125–0.5. These conservative unit/name-based rules are explicit in code
and in every admitted catalogue row; they are not inferred clinical categories.
Two concentrated condiment rows have specific rules: OSR096 tamarind chutney
5–20 ml in 5 ml increments, OSR097 pav bhaji masala 0.5–5 g in 0.5 g increments.
These are transparent research assumptions, not clinically validated portions.
Recorded input portions may differ from recommendation rules: the diary records
what was eaten, while the optimizer uses discrete recommendation quantities.

The workbook has no reliable meal-role classification. Flexible-v2 therefore
does not impose the old hand-assigned breakfast-main or lunch-staple/curry rules
on unclassified foods. Foods are available at any eating occasion. Nutrition and
portion feasibility do not establish culinary appropriateness, allergy safety,
vegetarian compatibility or clinical suitability; those filters are not present.

## Variable meals and dishes

Users can add named eating occasions and remove meals. There is no fixed four-meal
or three-dish representation. Each input day remains an independent experiment.
An empty recorded meal stays empty. Each non-empty meal can contain from one dish
to its recorded distinct-food count plus two. Thus a meal recorded with six dishes
can produce one to eight dishes. Repeated foods within a meal are combined into
one portion in the diary and prohibited in recommendations.

The chromosome has two genes per available dish slot. Food identity selects from
the complete catalogue. Portion genes below 0.25 encode an absent dish; remaining
values map to the food's discrete portion range. This gives optional dishes a
meaningful search probability regardless of catalogue size. APPO's meal-block
crossover, memory, bounded repair and adaptive search operate on dynamic blocks.

The local service has a resource guard of 256 search slots per day (recorded dishes
plus two per non-empty meal), and at most 256 meal names of up to 80 characters.
This is an operational bound, not a dietary rule or an unlimited-scale claim.
Diary batches remain limited to 14 days and pending job cohorts to 210 jobs.

## Shared scientific evaluation

All six algorithms use the same decoded representation and four objectives:
nutrition deviation, habit deviation, repetition penalty and meal-energy-share
deviation. Energy shares derive from the recorded day's meals rather than fixed
breakfast/lunch/snack/dinner percentages. One non-empty meal has zero distribution
deviation; that objective carries no discriminating information for that pattern.

There are **9 + 4 × named-meal-count** inequalities:

1. Original daily nutrient bounds: energy 90–110%, protein 90–115%, carbohydrate
   and fat 80–120%, fibre at least 80% of the profile target.
2. Per-meal minimum dishes, maximum dishes, duplicate-food count, and aggregate
   catalogue/portion validity. Empty meals have both minimum and maximum zero.

Every returned solution is re-decoded and checked independently of search
selection; objectives are recomputed without MOEA/D's search penalty. Snapshots
record version, dimensions, named constraints, slot capacities, energy shares,
catalogue size, profile, input day and source/workbook fingerprints.

APPO repair trials count toward its exact budget. MOEA/D retains whole generations
of 84 candidates (14,952 at a requested budget of 15,000). Other algorithms use
15,000 evaluations. SPEA2 uses raw-distance survival consistently for flexible-v2
because the installed normalized survival divides by zero for constant objectives.
All objectives are dimensionless. Legacy pilot SPEA2 is unchanged.

No fallback silently replaces a baseline with APPO or fabricates a feasible diet.
`no_feasible` is a completed search outcome, distinct from an execution failure.

## Verification

- 14 backend tests: accounts, ownership, snapshots, queue recovery, exports,
  catalogue admission and variable layouts including 1, 2, 5, 8 and 20 meals.
  Every admitted food is decoded and portion-validated; a 15-dish meal is tested.
- 8 original APPO regression tests passed, retaining pilot compatibility.
- 6 React tests passed; TypeScript and production build passed.
- Browser: custom Evening snack saved with Chicken sandwich, an expanded-catalogue
  food; search found 34 chicken foods; pagination advanced from 60 to 120 of 818;
  all five meal cards measured 400 px high during search.
- `scripts/verify_flexible.py`: twelve actual full-budget runs, six algorithms
  each on one-meal and five-meal patterns. Evidence is in
  `outputs/verification/flexible-v2.json`. Every returned diet passed its dynamic
  constraints and objective recomputation. MOPSO found no feasible diets on these
  two seed-42 checks; that is recorded rather than concealed. This does not prove
  APPO superior: compare repeated seeds and representative profiles separately.
- `scripts/verify_web_pipeline.py`: actual PostgreSQL queue, per-day snapshots,
  observed evaluation counts, independent constraints, recommendations and CSV/JSON
  exports. Current run evidence is in `.local/flexible-web-verification.json`.

Start with `Start-AmritAHARA.ps1`, open http://127.0.0.1:8000, and refresh the page
after upgrading. Saved old runs still display their original snapshots; create
a new experiment to use the expanded catalogue and variable meal formulation.
