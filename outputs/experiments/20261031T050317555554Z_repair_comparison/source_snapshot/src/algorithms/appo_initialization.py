
import numpy as np

from src.algorithms.appo_config import (
    APPOConfig,
    DEFAULT_APPO_CONFIG,
)
from src.diet_representation import (
    MEAL_NAMES,
    FOOD_SLOTS_PER_MEAL,
    get_serving_rule,
)


def _active_foods(pool):
    """Return all selectable foods except NONE."""
    return [
        (index, row)
        for index, row in pool.iterrows()
        if row["food_code"] != "NONE"
    ]


def _role_candidates(pool, role):
    """Return indices for foods with a specified role."""
    return [
        index
        for index, row in _active_foods(pool)
        if row["role"] == role
    ]


def _normalized_serving(servings, rule):
    """
    Convert a practical serving amount into the
    normalized [0, 1] optimizer representation.
    """
    minimum = float(rule["min"])
    maximum = float(rule["max"])

    if maximum <= minimum:
        return 0.0

    return float(
        np.clip(
            (float(servings) - minimum)
            / (maximum - minimum),
            0.0,
            1.0,
        )
    )


def _sample_serving_gene(
    rng,
    food_row,
    preferred_servings=None,
):
    """Sample or encode a valid normalized serving gene."""
    rule = get_serving_rule(food_row)

    if preferred_servings is not None:
        return _normalized_serving(
            preferred_servings,
            rule,
        )

    minimum = float(rule["min"])
    maximum = float(rule["max"])
    step = float(rule["step"])

    if step <= 0 or maximum <= minimum:
        return 0.0

    levels = (
        minimum
        + np.arange(
            int(round((maximum - minimum) / step)) + 1
        ) * step
    )

    levels = np.clip(levels, minimum, maximum)

    serving = float(rng.choice(levels))

    return _normalized_serving(serving, rule)


def _empty_index(pool):
    matches = pool.index[
        pool["food_code"] == "NONE"
    ].tolist()

    if len(matches) != 1:
        raise ValueError(
            "Each meal pool must contain exactly one NONE."
        )

    return int(matches[0])


def _choose_role_valid_indices(meal_name, pool, rng):
    """
    Choose 2 or 3 unique food indices while
    respecting the current meal-role structure.
    """
    if meal_name == "breakfast":
        required_roles = ["main"]

    elif meal_name in ("lunch", "dinner"):
        required_roles = [
            "staple",
            "protein_curry",
        ]

    elif meal_name == "snack":
        required_roles = ["snack_item"]

    else:
        raise ValueError(
            f"Unsupported meal: {meal_name}"
        )

    selected = []

    for role in required_roles:
        candidates = _role_candidates(pool, role)

        if not candidates:
            raise ValueError(
                f"{meal_name}: no foods for role {role}"
            )

        selected.append(int(rng.choice(candidates)))

    if meal_name == "breakfast":
        optional_roles = [
            "protein",
            "protein_curry",
            "accompaniment",
            "beverage",
        ]

    elif meal_name in ("lunch", "dinner"):
        optional_roles = ["side"]

    else:
        optional_roles = [
            "snack_item",
            "beverage",
            "accompaniment",
        ]

    while len(selected) < 2:
        candidates = [i for role in optional_roles
                      for i in _role_candidates(pool, role) if i not in selected]
        if not candidates:
            raise ValueError(f"{meal_name}: cannot construct two distinct role-valid foods")
        selected.append(int(rng.choice(candidates)))

    if (
        len(selected) < FOOD_SLOTS_PER_MEAL
        and rng.random() < 0.70
    ):
        rng.shuffle(optional_roles)

        for role in optional_roles:
            candidates = [
                i for i in _role_candidates(pool, role)
                if i not in selected
            ]

            # Keep at most one beverage in a snack.
            if meal_name == "snack" and role == "beverage":
                already_beverage = any(
                    pool.iloc[i]["role"] == "beverage"
                    for i in selected
                )
                if already_beverage:
                    continue

            if candidates:
                selected.append(int(rng.choice(candidates)))
                break

    return selected


def _encode_meal(
    pool,
    selected_indices,
    rng,
    preferred_servings=None,
):
    """Encode a meal into three food/serving pairs."""
    preferred_servings = preferred_servings or {}
    selected = list(selected_indices)

    while len(selected) < FOOD_SLOTS_PER_MEAL:
        selected.append(_empty_index(pool))

    rng.shuffle(selected)

    genes = []

    for index in selected[:FOOD_SLOTS_PER_MEAL]:
        food_row = pool.iloc[index]
        code = food_row["food_code"]

        if code == "NONE":
            serving_gene = 0.0
        else:
            serving_gene = _sample_serving_gene(
                rng,
                food_row,
                preferred_servings.get(code),
            )

        genes.extend([
            float(index),
            float(serving_gene),
        ])

    return genes


def _baseline_indices(meal_name, pool, existing_diet):
    """Find existing-diet foods inside a meal pool."""
    found = []
    servings = {}

    for item in existing_diet.get(meal_name, []):
        code = item["food_code"]

        matches = pool.index[
            pool["food_code"] == code
        ].tolist()

        if matches:
            index = int(matches[0])

            if index not in found:
                found.append(index)
                servings[code] = float(
                    item["servings"]
                )

    return found, servings


def _habit_guided_meal(
    meal_name,
    pool,
    existing_diet,
    rng,
):
    """
    Start with existing meal foods and sometimes
    replace one component with another valid food.
    """
    baseline, preferred = _baseline_indices(
        meal_name,
        pool,
        existing_diet,
    )

    if not baseline:
        indices = _choose_role_valid_indices(
            meal_name,
            pool,
            rng,
        )

        return _encode_meal(
            pool,
            indices,
            rng,
        )

    selected = list(baseline)

    # Retain all baseline foods in roughly half
    # of habit-guided candidates.
    if rng.random() < 0.50:
        return _encode_meal(
            pool,
            selected,
            rng,
            preferred,
        )

    # Use a role-compatible substitution.
    position = int(rng.integers(len(selected)))
    old_index = selected[position]
    old_role = pool.iloc[old_index]["role"]

    replacements = [
        i
        for i in _role_candidates(pool, old_role)
        if i not in selected
    ]

    if replacements:
        selected[position] = int(
            rng.choice(replacements)
        )

    # If fewer than two foods remain, fall
    # back to role-guided initialization.
    if len(selected) < 2:
        selected = _choose_role_valid_indices(
            meal_name,
            pool,
            rng,
        )

    return _encode_meal(
        pool,
        selected,
        rng,
        preferred,
    )


def initialize_appo_population(
    problem,
    existing_diet,
    config: APPOConfig = DEFAULT_APPO_CONFIG,
    rng=None,
):
    """
    Return an initial APPO population.

    Shape:
        (population_size, problem.n_var)

    The first fraction is habit-guided.
    The remaining candidates are role-guided.

    This function does not evaluate objectives
    or consume the function-evaluation budget.
    """
    if rng is None:
        rng = np.random.default_rng(config.seed)

    population = []

    habit_count = int(
        round(
            config.population_size
            * (config.baseline_seed_fraction if config.memory_enabled else 0.0)
        )
    )

    if not 0 <= habit_count <= config.population_size:
        raise ValueError(
            "baseline_seed_fraction must be within [0, 1]"
        )

    for candidate_number in range(
        config.population_size
    ):
        genes = []

        habit_guided = candidate_number < habit_count

        for meal_name in MEAL_NAMES:
            pool = problem.food_pools[meal_name]

            if habit_guided:
                meal_genes = _habit_guided_meal(
                    meal_name,
                    pool,
                    existing_diet,
                    rng,
                )
            else:
                selected = _choose_role_valid_indices(
                    meal_name,
                    pool,
                    rng,
                )

                meal_genes = _encode_meal(
                    pool,
                    selected,
                    rng,
                )

            genes.extend(meal_genes)

        chromosome = np.asarray(
            genes,
            dtype=float,
        )

        if len(chromosome) != problem.n_var:
            raise RuntimeError(
                "APPO chromosome length mismatch."
            )

        population.append(chromosome)

    return np.asarray(population, dtype=float)
