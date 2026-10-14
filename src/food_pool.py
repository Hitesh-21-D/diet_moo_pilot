MEAL_FOOD_CODES = {
    "breakfast": [
        "ASC024",  # Egg sandwich
        "ASC037",  # Egg and tomato sandwich
        "ASC056",  # Boiled egg
        "ASC057",  # Fried egg
        "ASC058",  # Poached egg
        "ASC059",  # Scrambled egg
        "ASC051",  # Cornflakes with milk
        "ASC042",  # Paneer pea sandwich
        "BFP042",  # Bread upma
        "ASC052",  # Rice flakes / Aval
    ],

    "lunch": [
        "ASC113",  # Boiled rice
        "ASC124",  # Lemon rice
        "ASC126",  # Curd rice
        "ASC128",  # Spanish rice
        "ASC129",  # Chinese fried rice
        "ASC167",  # Sambar
        "ASC191",  # Matar paneer
        "ASC195",  # Paneer curry
        "ASC215",  # Palak paneer
        "ASC226",  # Kadhai paneer
    ],

    "snack": [
        "ASC016",  # Banana milkshake
        "ASC017",  # Mango milkshake
        "ASC018",  # Pineapple milkshake
        "ASC019",  # Orange milkshake
        "ASC051",  # Cornflakes with milk
        "BFP326",  # Banana raita
        "ASC423",  # Banana cake
        "ASC450",  # Ginger bread man
        "ASC452",  # Short bread cookies
    ],

    "dinner": [
        "ASC113",  # Boiled rice
        "ASC124",  # Lemon rice
        "ASC126",  # Curd rice
        "ASC167",  # Sambar
        "ASC191",  # Matar paneer
        "ASC195",  # Paneer curry
        "ASC215",  # Palak paneer
        "ASC221",  # Shahi paneer
        "ASC222",  # Paneer in butter sauce
        "ASC226",  # Kadhai paneer
    ],
}


def build_food_pools(df):
    """
    Build meal-specific candidate food pools from INDB.

    Only foods explicitly listed in MEAL_FOOD_CODES are used
    in this pilot.
    """

    pools = {}

    for meal_name, food_codes in MEAL_FOOD_CODES.items():

        pool = df[
            df["food_code"].isin(food_codes)
        ].copy()

        missing_codes = [
            code
            for code in food_codes
            if code not in pool["food_code"].values
        ]

        if missing_codes:
            print(
                f"WARNING: Missing foods in {meal_name}: "
                f"{missing_codes}"
            )

        pool = pool.reset_index(drop=True)

        pools[meal_name] = pool

    return pools


def print_food_pools(pools):
    """
    Print meal-specific food pools.
    """

    for meal_name, pool in pools.items():

        print("\n" + "=" * 60)
        print(
            f"{meal_name.upper()} FOOD POOL "
            f"({len(pool)} foods)"
        )
        print("=" * 60)

        print(
            pool[
                [
                    "food_code",
                    "food_name",
                    "servings_unit",
                    "energy_kcal",
                    "protein_g",
                    "carb_g",
                    "fat_g",
                    "fibre_g",
                ]
            ].to_string(
                index=False
            )
        )