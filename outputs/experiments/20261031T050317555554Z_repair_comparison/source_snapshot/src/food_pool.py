import pandas as pd


# ============================================================
# Expanded meal-specific food pools
# ============================================================

MEAL_FOOD_CODES = {

    "breakfast": [
        "ASC144",  # Idli
        "BFP148",  # Plain dosa
        "ASC146",  # Masala dosa
        "BFP039",  # Rava upma
        "BFP043",  # Vegetable upma
        "BFP044",  # Poha
        "BFP045",  # Vegetable poha
        "BFP042",  # Bread upma
        "ASC056",  # Boiled egg
        "ASC059",  # Scrambled egg
        "ASC024",  # Egg sandwich
        "ASC167",  # Sambar
        "ASC386",  # Coconut chutney
        "ASC385",  # Peanut chutney
        "ASC001",  # Tea
    ],

    "lunch": [
        "ASC113",  # Boiled rice
        "ASC124",  # Lemon rice
        "ASC126",  # Curd rice
        "ASC115",  # Mixed vegetable pulao
        "ASC096",  # Chapati / Roti
        "ASC167",  # Sambar
        "ASC151",  # Moong dal
        "ASC155",  # Mixed dal
        "ASC191",  # Matar paneer
        "ASC195",  # Paneer curry
        "ASC215",  # Palak paneer
        "BFP241",  # Vegetable curry with coconut
        "BFP269",  # Bhindi sabzi
        "ASC261",  # Mixed vegetable salad with curd
        "ASC273",  # Cucumber raita
    ],

    "snack": [
        "ASC001",  # Tea
        "ASC016",  # Banana milkshake
        "ASC017",  # Mango milkshake
        "ASC021",  # Sweet lassi
        "ASC022",  # Salted lassi
        "BFP044",  # Poha
        "BFP045",  # Vegetable poha
        "ASC170",  # Sprouted moong chaat
        "ASC259",  # Sprouted moong salad
        "ASC265",  # Fruit salad
        "ASC054",  # Murmura / Puffed rice
        "ASC052",  # Rice flakes / Aval
        "ASC385",  # Peanut chutney
        "BFP326",  # Banana raita
    ],

    "dinner": [
        "ASC096",  # Chapati / Roti
        "ASC113",  # Boiled rice
        "ASC124",  # Lemon rice
        "ASC126",  # Curd rice
        "BFP144",  # Plain khichdi
        "ASC167",  # Sambar
        "ASC151",  # Moong dal
        "ASC155",  # Mixed dal
        "ASC191",  # Matar paneer
        "ASC195",  # Paneer curry
        "ASC215",  # Palak paneer
        "ASC226",  # Kadhai paneer
        "BFP241",  # Vegetable curry with coconut
        "BFP269",  # Bhindi sabzi
        "ASC261",  # Mixed vegetable salad with curd
        "ASC273",  # Cucumber raita
    ],
}


# ============================================================
# Meal-specific food roles
# ============================================================
#
# Roles are used by the constraint system to prevent
# unrealistic meal combinations.
#
# The same food can theoretically have a different role
# in a different meal.
# ============================================================

MEAL_FOOD_ROLES = {

    "breakfast": {

        "ASC144": "main",
        "BFP148": "main",
        "ASC146": "main",
        "BFP039": "main",
        "BFP043": "main",
        "BFP044": "main",
        "BFP045": "main",
        "BFP042": "main",
        "ASC024": "main",

        "ASC056": "protein",
        "ASC059": "protein",

        "ASC167": "protein_curry",

        "ASC386": "accompaniment",
        "ASC385": "accompaniment",

        "ASC001": "beverage",
    },

    "lunch": {

        "ASC113": "staple",
        "ASC124": "staple",
        "ASC126": "staple",
        "ASC115": "staple",
        "ASC096": "staple",

        "ASC167": "protein_curry",
        "ASC151": "protein_curry",
        "ASC155": "protein_curry",
        "ASC191": "protein_curry",
        "ASC195": "protein_curry",
        "ASC215": "protein_curry",

        "BFP241": "side",
        "BFP269": "side",
        "ASC261": "side",
        "ASC273": "side",
    },

    "snack": {

        "ASC001": "beverage",
        "ASC016": "beverage",
        "ASC017": "beverage",
        "ASC021": "beverage",
        "ASC022": "beverage",

        "BFP044": "snack_item",
        "BFP045": "snack_item",
        "ASC170": "snack_item",
        "ASC259": "snack_item",
        "ASC265": "snack_item",

        "ASC054": "snack_item",
        "ASC052": "snack_item",
        "BFP326": "snack_item",

        "ASC385": "accompaniment",
    },

    "dinner": {

        "ASC096": "staple",
        "ASC113": "staple",
        "ASC124": "staple",
        "ASC126": "staple",
        "BFP144": "staple",

        "ASC167": "protein_curry",
        "ASC151": "protein_curry",
        "ASC155": "protein_curry",
        "ASC191": "protein_curry",
        "ASC195": "protein_curry",
        "ASC215": "protein_curry",
        "ASC226": "protein_curry",

        "BFP241": "side",
        "BFP269": "side",
        "ASC261": "side",
        "ASC273": "side",
    },
}


# ============================================================
# Empty-slot pseudo food
# ============================================================
#
# This lets a meal contain only two foods even though the
# chromosome still contains three maximum slots.
# ============================================================

EMPTY_FOOD = {
    "food_code": "NONE",
    "food_name": "No food selected",
    "servings_unit": "none",
    "energy_kcal": 0.0,
    "protein_g": 0.0,
    "carb_g": 0.0,
    "fat_g": 0.0,
    "fibre_g": 0.0,
    "role": "empty",
}


def build_food_pools(df):

    food_pools = {}

    missing_codes = []

    for meal_name, food_codes in (
        MEAL_FOOD_CODES.items()
    ):

        records = []

        role_map = MEAL_FOOD_ROLES[
            meal_name
        ]

        for food_code in food_codes:

            match = df[
                df["food_code"]
                == food_code
            ]

            if match.empty:

                missing_codes.append(
                    (
                        meal_name,
                        food_code,
                    )
                )

                continue

            record = (
                match.iloc[0]
                .to_dict()
            )

            record["role"] = (
                role_map[
                    food_code
                ]
            )

            records.append(
                record
            )

        # Allow one optional empty slot.
        records.append(
            EMPTY_FOOD.copy()
        )

        food_pools[
            meal_name
        ] = pd.DataFrame(
            records
        )

    if missing_codes:

        message = [
            "The following configured food codes "
            "were not found in the cleaned INDB dataset:"
        ]

        for meal, code in missing_codes:

            message.append(
                f"  {meal}: {code}"
            )

        raise ValueError(
            "\n".join(message)
        )

    return food_pools


def print_food_pools(
    food_pools
):

    for meal_name, pool in (
        food_pools.items()
    ):

        real_foods = pool[
            pool["food_code"]
            != "NONE"
        ]

        print(
            "\n"
            + "=" * 70
        )

        print(
            f"{meal_name.upper()} "
            f"FOOD POOL "
            f"({len(real_foods)} foods "
            f"+ optional NONE)"
        )

        print(
            "=" * 70
        )

        columns = [
            "food_code",
            "food_name",
            "role",
            "servings_unit",
            "energy_kcal",
            "protein_g",
            "carb_g",
            "fat_g",
            "fibre_g",
        ]

        print(
            pool[
                columns
            ].to_string(
                index=False
            )
        )