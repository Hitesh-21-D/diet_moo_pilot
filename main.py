from config.user_profile import USER_PROFILE

from src.data_loader import (
    load_indb,
    search_foods,
)

from src.nutrient_targets import (
    calculate_bmr,
    calculate_tdee,
    calculate_nutrient_targets,
)

from src.food_pool import (
    build_food_pools,
    print_food_pools,
)


def print_user_details():
    print("\n" + "=" * 60)
    print("PILOT USER")
    print("=" * 60)

    print(f"Age: {USER_PROFILE['age']}")
    print(f"Sex: {USER_PROFILE['sex']}")
    print(f"Height: {USER_PROFILE['height_cm']} cm")
    print(f"Weight: {USER_PROFILE['weight_kg']} kg")
    print(f"Goal: {USER_PROFILE['goal']}")


def print_targets():
    bmr = calculate_bmr(USER_PROFILE)
    tdee = calculate_tdee(USER_PROFILE)
    targets = calculate_nutrient_targets(USER_PROFILE)

    print("\n" + "=" * 60)
    print("NUTRITION TARGETS")
    print("=" * 60)

    print(f"BMR: {bmr:.2f} kcal")
    print(f"TDEE: {tdee:.2f} kcal")

    print()

    for nutrient, value in targets.items():
        print(f"{nutrient:<15}: {value}")


def test_food_search(df):
    search_terms = [
        "egg",
        "rice",
        "milk",
        "paneer",
        "banana",
        "sambar",
        "bread",
    ]

    for term in search_terms:
        print("\n" + "=" * 60)
        print(f"INDB SEARCH: {term.upper()}")
        print("=" * 60)

        matches = search_foods(
            df,
            term,
            limit=10,
        )

        if matches.empty:
            print("No matching foods found.")
        else:
            print(
                matches.to_string(
                    index=False
                )
            )


def main():
    print_user_details()
    print_targets()

    print("\n" + "=" * 60)
    print("LOADING ANUVAAD INDB")
    print("=" * 60)

    df = load_indb()

    food_pools = build_food_pools(df)

    print_food_pools(food_pools)

    print("\nFirst 5 foods:")

    print(
        df.head().to_string(
            index=False
        )
    )

    test_food_search(df)


if __name__ == "__main__":
    main()