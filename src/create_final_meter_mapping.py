from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
CONFIG_DIR = BASE_DIR / "config"

DRAFT_FILE = OUTPUT_DIR / "draft_meter_mapping_from_portfolio.xlsx"
MAPPING_FILE = CONFIG_DIR / "meter_mapping.csv"


TA_TEST_MAPPING = {
    ("TA", "Chilled Water"): {
        "test_property_id": "19980855",
        "test_meter_id": "25965184",
    }
}


FINAL_COLUMNS = [
    "building_code",
    "building_name",
    "utility",
    "test_property_id",
    "test_meter_id",
    "live_property_id",
    "live_meter_id",
    "unit",
]


def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def main():
    print("CSU ENERGY STAR - Create Final Meter Mapping")
    print("--------------------------------------------")

    if not DRAFT_FILE.exists():
        raise FileNotFoundError(f"Missing draft file: {DRAFT_FILE}")

    CONFIG_DIR.mkdir(exist_ok=True)

    df = pd.read_excel(DRAFT_FILE, sheet_name="Draft Mapping", dtype=str)

    allowed_statuses = ["MATCHED", "MATCHED_MANUAL_OVERRIDE"]

    df = df[df["mapping_status"].isin(allowed_statuses)].copy()

    final_rows = []

    for _, row in df.iterrows():
        building_code = clean_text(row.get("building_code")).upper()
        utility = clean_text(row.get("utility"))

        test_property_id = ""
        test_meter_id = ""

        test_override = TA_TEST_MAPPING.get((building_code, utility))
        if test_override:
            test_property_id = test_override["test_property_id"]
            test_meter_id = test_override["test_meter_id"]

        final_rows.append(
            {
                "building_code": building_code,
                "building_name": clean_text(row.get("building_name")),
                "utility": utility,
                "test_property_id": test_property_id,
                "test_meter_id": test_meter_id,
                "live_property_id": clean_text(row.get("live_property_id")),
                "live_meter_id": clean_text(row.get("live_meter_id")),
                "unit": clean_text(row.get("unit")),
            }
        )

    final_df = pd.DataFrame(final_rows, columns=FINAL_COLUMNS)

    final_df = final_df.drop_duplicates(
        subset=["building_code", "utility"],
        keep="first",
    )

    final_df = final_df.sort_values(["utility", "building_code"])

    final_df.to_csv(MAPPING_FILE, index=False)

    print("\nCreated/Updated:")
    print(MAPPING_FILE)

    print("\nFinal mapping summary:")
    print(final_df["utility"].value_counts())

    print("\nRows with test meter IDs:")
    test_rows = final_df[final_df["test_meter_id"] != ""]

    if test_rows.empty:
        print("No test meter IDs found.")
    else:
        print(
            test_rows[
                ["building_code", "utility", "test_property_id", "test_meter_id"]
            ].to_string(index=False)
        )

    print("\nDone. Mapping file updated. Nothing uploaded.")


if __name__ == "__main__":
    main()