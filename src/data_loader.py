from pathlib import Path
import pandas as pd


REQUIRED_COLUMNS = [
    "food_code",
    "food_name",
    "servings_unit",
    "unit_serving_energy_kcal",
    "unit_serving_protein_g",
    "unit_serving_carb_g",
    "unit_serving_fat_g",
    "unit_serving_fibre_g",
]


NUTRIENT_COLUMNS = [
    "unit_serving_energy_kcal",
    "unit_serving_protein_g",
    "unit_serving_carb_g",
    "unit_serving_fat_g",
    "unit_serving_fibre_g",
]


def get_project_root():
    return Path(__file__).resolve().parent.parent


def get_dataset_path():
    return get_project_root() / "data" / "INDB.xlsx"


def load_indb():
    """
    Load Anuvaad INDB using serving-based nutrient values.

    Each row represents a food item with a natural serving unit,
    such as:
        egg
        bowl
        plate
        cup
        slice
        glass
        piece
    """

    dataset_path = get_dataset_path()

    if not dataset_path.exists():
        raise FileNotFoundError(
            f"INDB dataset not found at:\n{dataset_path}"
        )

    df = pd.read_excel(
        dataset_path,
        sheet_name="Nutrient Data",
    )

    print(
        f"Original INDB shape: "
        f"{df.shape[0]} rows x {df.shape[1]} columns"
    )

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing_columns)
        )

    df = df[REQUIRED_COLUMNS].copy()

    # Foods must have a usable name and serving unit.
    df = df.dropna(
        subset=[
            "food_name",
            "servings_unit",
        ]
    )

    df["food_name"] = (
        df["food_name"]
        .astype(str)
        .str.strip()
    )

    df["servings_unit"] = (
        df["servings_unit"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    # Convert nutrient columns to numeric.
    for column in NUTRIENT_COLUMNS:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    # For the optimization pilot, we only use foods with
    # complete serving-based nutrient information.
    df = df.dropna(
        subset=NUTRIENT_COLUMNS
    )

    # Remove impossible negative values.
    for column in NUTRIENT_COLUMNS:
        df = df[df[column] >= 0]

    # Basic plausibility filtering for the pilot.
    # These thresholds remove extreme serving records that would
    # destabilize the optimization search.

    df = df[
        (df["unit_serving_energy_kcal"] <= 1500)
        & (df["unit_serving_protein_g"] <= 100)
        & (df["unit_serving_carb_g"] <= 200)
        & (df["unit_serving_fat_g"] <= 100)
        & (df["unit_serving_fibre_g"] <= 50)
    ]
    
    # Rename serving nutrient fields to shorter internal names.
    df = df.rename(
        columns={
            "unit_serving_energy_kcal": "energy_kcal",
            "unit_serving_protein_g": "protein_g",
            "unit_serving_carb_g": "carb_g",
            "unit_serving_fat_g": "fat_g",
            "unit_serving_fibre_g": "fibre_g",
        }
    )

    df = df.reset_index(drop=True)

    print(
        f"Serving-based pilot dataset shape: "
        f"{df.shape[0]} rows x {df.shape[1]} columns"
    )

    return df


def search_foods(df, search_term, limit=20):
    search_term = search_term.lower().strip()

    matches = df[
        df["food_name"]
        .str.lower()
        .str.contains(
            search_term,
            na=False,
        )
    ]

    return matches.head(limit)