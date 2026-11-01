USER_PROFILE = {
    "age": 22,
    "sex": "male",
    "height_cm": 178,
    "weight_kg": 57.5,

    "activity_factor": 1.55,

    "goal": "weight_gain",

    "calorie_adjustment": 300,

    "meals_per_day": 4,

    # ---------------------------------------------------------
    # Synthetic Existing Diet
    # ---------------------------------------------------------
    #
    # This represents the user's current dietary habit.
    # It is intentionally realistic and recognizable for
    # the expanded Indian-diet pilot.
    #
    # IMPORTANT:
    # serving quantities correspond to INDB serving units.
    # ---------------------------------------------------------

    "existing_diet": {

        "breakfast": [
            {
                "food_code": "ASC144",
                "food": "Idli",
                "servings": 3.0,
            },
            {
                "food_code": "ASC167",
                "food": "Sambar",
                "servings": 1.0,
            },
            {
                "food_code": "ASC386",
                "food": "Coconut chutney",
                "servings": 1.0,
            },
        ],

        "lunch": [
            {
                "food_code": "ASC113",
                "food": "Boiled rice",
                "servings": 1.0,
            },
            {
                "food_code": "ASC167",
                "food": "Sambar",
                "servings": 1.0,
            },
            {
                "food_code": "ASC261",
                "food": (
                    "Mixed vegetable salad "
                    "with curd sauce"
                ),
                "servings": 0.5,
            },
        ],

        "snack": [
            {
                "food_code": "BFP045",
                "food": "Vegetable poha",
                "servings": 1.0,
            },
            {
                "food_code": "ASC001",
                "food": "Hot tea",
                "servings": 1.0,
            },
        ],

        "dinner": [
            {
                "food_code": "ASC096",
                "food": "Chapati/Roti",
                "servings": 3.0,
            },
            {
                "food_code": "ASC191",
                "food": "Matar paneer",
                "servings": 1.0,
            },
        ],
    },
}