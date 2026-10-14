def calculate_bmr(user_profile):
    weight = user_profile["weight_kg"]
    height = user_profile["height_cm"]
    age = user_profile["age"]
    sex = user_profile["sex"].lower()

    if sex == "male":
        return (10 * weight) + (6.25 * height) - (5 * age) + 5

    if sex == "female":
        return (10 * weight) + (6.25 * height) - (5 * age) - 161

    raise ValueError("sex must be either 'male' or 'female'")


def calculate_tdee(user_profile):
    bmr = calculate_bmr(user_profile)
    return bmr * user_profile["activity_factor"]


def calculate_nutrient_targets(user_profile):
    tdee = calculate_tdee(user_profile)

    goal = user_profile["goal"].lower()
    calorie_adjustment = user_profile.get("calorie_adjustment", 0)

    if goal == "weight_gain":
        calorie_target = tdee + calorie_adjustment

    elif goal == "weight_loss":
        calorie_target = tdee - abs(calorie_adjustment)

    elif goal == "maintenance":
        calorie_target = tdee

    else:
        raise ValueError(f"Unsupported goal: {goal}")

    weight = user_profile["weight_kg"]

    protein_target = weight * 1.8
    fat_target = weight * 1.0

    protein_calories = protein_target * 4
    fat_calories = fat_target * 9

    carb_calories = (
        calorie_target
        - protein_calories
        - fat_calories
    )

    carb_target = carb_calories / 4

    fibre_target = 30.0

    return {
        "energy_kcal": round(calorie_target, 2),
        "protein_g": round(protein_target, 2),
        "carb_g": round(carb_target, 2),
        "fat_g": round(fat_target, 2),
        "fibre_g": round(fibre_target, 2),
    }