import numpy as np


MEAL_NAMES = [
    "breakfast",
    "lunch",
    "snack",
    "dinner",
]


FOOD_SLOTS_PER_MEAL = 3


# ============================================================
# Raw optimizer bounds
# ============================================================
#
# The optimizer operates on a generic serving variable.
# Actual food-specific serving rules are applied during
# decoding.
# ============================================================

RAW_SERVING_MIN = 0.0
RAW_SERVING_MAX = 1.0


# ============================================================
# Food-specific serving rules
# ============================================================
#
# Only foods requiring special practical handling need to
# appear here.
#
# Other foods use role-based defaults below.
# ============================================================

FOOD_SERVING_RULES = {

    # Idli
    "ASC144": {
        "min": 1.0,
        "max": 4.0,
        "step": 1.0,
    },

    # Chapati / Roti
    "ASC096": {
        "min": 1.0,
        "max": 4.0,
        "step": 1.0,
    },

    # Plain dosa
    "BFP148": {
        "min": 0.5,
        "max": 2.0,
        "step": 0.5,
    },

    # Masala dosa
    "ASC146": {
        "min": 0.5,
        "max": 2.0,
        "step": 0.5,
    },

    # Boiled egg
    "ASC056": {
        "min": 1.0,
        "max": 3.0,
        "step": 1.0,
    },

    # Scrambled egg
    "ASC059": {
        "min": 1.0,
        "max": 3.0,
        "step": 1.0,
    },

    # Tea
    "ASC001": {
        "min": 0.5,
        "max": 1.0,
        "step": 0.5,
    },

    # Coconut chutney
    "ASC386": {
        "min": 0.25,
        "max": 1.0,
        "step": 0.25,
    },

    # Peanut chutney
    "ASC385": {
        "min": 0.25,
        "max": 1.0,
        "step": 0.25,
    },

    # Banana raita
    "BFP326": {
        "min": 0.25,
        "max": 1.0,
        "step": 0.25,
    },

    # Fruit salad
    "ASC265": {
        "min": 0.5,
        "max": 1.5,
        "step": 0.25,
    },

    # Sprouted moong salad
    "ASC259": {
        "min": 0.5,
        "max": 1.5,
        "step": 0.25,
    },
}


# ============================================================
# Default serving rules according to meal role
# ============================================================

ROLE_SERVING_RULES = {

    "main": {
        "min": 0.5,
        "max": 2.0,
        "step": 0.25,
    },

    "staple": {
        "min": 0.5,
        "max": 2.0,
        "step": 0.25,
    },

    "protein": {
        "min": 0.5,
        "max": 2.0,
        "step": 0.5,
    },

    "protein_curry": {
        "min": 0.25,
        "max": 1.5,
        "step": 0.25,
    },

    "side": {
        "min": 0.25,
        "max": 1.0,
        "step": 0.25,
    },

    "snack_item": {
        "min": 0.5,
        "max": 2.0,
        "step": 0.25,
    },

    "beverage": {
        "min": 0.5,
        "max": 1.0,
        "step": 0.5,
    },

    "accompaniment": {
        "min": 0.25,
        "max": 1.0,
        "step": 0.25,
    },

    "empty": {
        "min": 0.0,
        "max": 0.0,
        "step": 0.0,
    },
}


def chromosome_length():

    return (
        len(MEAL_NAMES)
        * FOOD_SLOTS_PER_MEAL
        * 2
    )


def get_serving_rule(
    food
):

    food_code = food[
        "food_code"
    ]

    if food_code == "NONE":

        return {
            "min": 0.0,
            "max": 0.0,
            "step": 0.0,
        }

    if food_code in (
        FOOD_SERVING_RULES
    ):

        return (
            FOOD_SERVING_RULES[
                food_code
            ]
        )

    role = food.get(
        "role",
        "side",
    )

    return (
        ROLE_SERVING_RULES[
            role
        ]
    )


def quantize_servings(
    raw_value,
    minimum,
    maximum,
    step,
):
    """
    Convert a normalized optimizer gene in [0, 1]
    into a food-specific practical serving quantity.

    Example:

        raw = 0.0  -> minimum serving
        raw = 1.0  -> maximum serving

    The mapped quantity is then rounded to the
    food-specific serving increment.
    """

    if step <= 0:
        return 0.0

    raw_value = float(
        np.clip(
            raw_value,
            0.0,
            1.0,
        )
    )

    mapped_value = (
        minimum
        + raw_value
        * (
            maximum
            - minimum
        )
    )

    steps = round(
        (
            mapped_value
            - minimum
        )
        / step
    )

    quantized = (
        minimum
        + steps * step
    )

    quantized = np.clip(
        quantized,
        minimum,
        maximum,
    )

    return float(
        quantized
    )

def decode_chromosome(
    chromosome,
    food_pools,
):

    chromosome = np.asarray(
        chromosome,
        dtype=float,
    )

    diet = {}

    cursor = 0

    for meal_name in MEAL_NAMES:

        meal_foods = []

        pool = food_pools[
            meal_name
        ]

        pool_size = len(
            pool
        )

        for _ in range(
            FOOD_SLOTS_PER_MEAL
        ):

            raw_food_index = (
                chromosome[
                    cursor
                ]
            )

            raw_servings = (
                chromosome[
                    cursor + 1
                ]
            )

            cursor += 2

            food_index = int(
                round(
                    raw_food_index
                )
            )

            food_index = int(
                np.clip(
                    food_index,
                    0,
                    pool_size - 1,
                )
            )

            food = (
                pool.iloc[
                    food_index
                ]
                .to_dict()
            )

            rule = (
                get_serving_rule(
                    food
                )
            )

            servings = (
                quantize_servings(
                    raw_value=raw_servings,
                    minimum=rule[
                        "min"
                    ],
                    maximum=rule[
                        "max"
                    ],
                    step=rule[
                        "step"
                    ],
                )
            )

            if (
                food[
                    "food_code"
                ]
                == "NONE"
            ):

                servings = 0.0

            meal_foods.append(
                {
                    "food_code":
                        food[
                            "food_code"
                        ],

                    "food_name":
                        food[
                            "food_name"
                        ],

                    "role":
                        food[
                            "role"
                        ],

                    "serving_unit":
                        food[
                            "servings_unit"
                        ],

                    "servings":
                        servings,

                    "energy_kcal":
                        (
                            food[
                                "energy_kcal"
                            ]
                            * servings
                        ),

                    "protein_g":
                        (
                            food[
                                "protein_g"
                            ]
                            * servings
                        ),

                    "carb_g":
                        (
                            food[
                                "carb_g"
                            ]
                            * servings
                        ),

                    "fat_g":
                        (
                            food[
                                "fat_g"
                            ]
                            * servings
                        ),

                    "fibre_g":
                        (
                            food[
                                "fibre_g"
                            ]
                            * servings
                        ),
                }
            )

        diet[
            meal_name
        ] = meal_foods

    return diet


def calculate_diet_totals(
    diet
):

    totals = {
        "energy_kcal": 0.0,
        "protein_g": 0.0,
        "carb_g": 0.0,
        "fat_g": 0.0,
        "fibre_g": 0.0,
    }

    for foods in diet.values():

        for food in foods:

            if (
                food[
                    "food_code"
                ]
                == "NONE"
            ):
                continue

            for nutrient in totals:

                totals[
                    nutrient
                ] += food[
                    nutrient
                ]

    return totals


def calculate_meal_totals(
    diet
):

    meal_totals = {}

    for meal_name, foods in (
        diet.items()
    ):

        totals = {
            "energy_kcal": 0.0,
            "protein_g": 0.0,
            "carb_g": 0.0,
            "fat_g": 0.0,
            "fibre_g": 0.0,
        }

        for food in foods:

            if (
                food[
                    "food_code"
                ]
                == "NONE"
            ):
                continue

            for nutrient in totals:

                totals[
                    nutrient
                ] += food[
                    nutrient
                ]

        meal_totals[
            meal_name
        ] = totals

    return meal_totals