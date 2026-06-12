from pathlib import Path
import re
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"

PORTFOLIO_FILE = INPUT_DIR / "My-Portfolio.xlsx"
PAYMENT_EXTRACT_FILE = OUTPUT_DIR / "current_payment_matchup_extract.xlsx"
OUTPUT_FILE = OUTPUT_DIR / "draft_meter_mapping_from_portfolio.xlsx"


MANUAL_MAPPING_OVERRIDES = {
    ("KF", "Natural Gas"): {
        "meter_name": "KF_NATGAS",
        "review_notes": "Manual override: KF mapped to primary Krenzler Field gas meter",
    },
    ("KFA", "Natural Gas"): {
        "meter_name": "KF_AUX_NATGAS",
        "review_notes": "Manual override: KFA mapped to auxiliary Krenzler Field gas meter",
    },
}


REQUIRED_METER_COLUMNS = [
    "Property Name",
    "Portfolio Manager ID",
    "Portfolio Manager Meter ID",
    "Meter Name",
    "Meter Type",
    "Units",
]


def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def normalize_id(value):
    if pd.isna(value):
        return ""

    try:
        return str(int(float(value)))
    except Exception:
        return str(value).strip()


def find_header_row(file_path, sheet_name, required_columns):
    """
    ENERGY STAR export has report title rows before the real table header.
    This function automatically finds the row containing the real headers.
    """
    raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None, dtype=str)

    for index, row in raw.iterrows():
        row_values = [clean_text(v) for v in row.tolist()]
        matches = sum(1 for col in required_columns if col in row_values)

        if matches >= len(required_columns):
            return index

    raise ValueError(f"Could not find header row in sheet {sheet_name}")


def guess_building_code_from_name(name):
    """
    Tries to extract building code from property or meter name.

    Examples:
    Administration Center (AC) -> AC
    Theater Arts (TA) -Formerly Middough Building (MB)- -> TA
    """
    text = clean_text(name)

    # Best case: building code in parentheses.
    # Use the FIRST code, because some names have old building codes later.
    # Example: Theater Arts (TA) -Formerly Middough Building (MB)- should return TA.
    matches = re.findall(r"\(([A-Z0-9]{1,5})\)", text)
    if matches:
        return matches[0].upper()

    # Fallback: first short all-caps token
    parts = re.split(r"[\s\-_]+", text)

    skip_words = {
        "CSU",
        "CLEVELAND",
        "STATE",
        "UNIVERSITY",
        "BUILDING",
        "HALL",
        "CENTER",
        "METERS",
        "METER",
        "WATER",
        "GAS",
        "NATURAL",
        "CHILLED",
        "STEAM",
        "ELECTRIC",
        "GRID",
        "POTABLE",
        "INDOOR",
        "OUTDOOR",
        "MIXED",
        "DISTRICT",
        "FORMERLY",
    }

    for part in parts:
        part = part.strip().upper()

        if 1 <= len(part) <= 5 and part.isalnum() and part not in skip_words:
            return part

    return ""


def classify_utility(meter_type, meter_name):
    """
    Classify ENERGY STAR meter types into the same utility names
    used by our Payment Matchup extractor.

    Payment Matchup utility names:
    - Natural Gas
    - Water
    - Chilled Water

    ENERGY STAR may call water meters:
    - Potable: Mixed Indoor/Outdoor
    - Potable Indoor
    """
    text = f"{clean_text(meter_type)} {clean_text(meter_name)}".lower()

    # Chilled Water must be checked before general Water,
    # because "District Chilled Water" also contains the word "water".
    if "chilled water" in text or "district chilled" in text:
        return "Chilled Water"

    # Natural Gas meters may appear as Natural Gas, NATGAS, or gas.
    if "natural gas" in text or "natgas" in text or "gas" in text:
        return "Natural Gas"

    # ENERGY STAR water meters are usually labeled as Potable.
    if "potable" in text or "water" in text:
        return "Water"

    return "Other"


def load_portfolio_meters():
    if not PORTFOLIO_FILE.exists():
        raise FileNotFoundError(f"Missing file: {PORTFOLIO_FILE}")

    header_row = find_header_row(
        PORTFOLIO_FILE,
        "Meters",
        REQUIRED_METER_COLUMNS,
    )

    print(f"Detected Meters header row: {header_row + 1}")

    df = pd.read_excel(
        PORTFOLIO_FILE,
        sheet_name="Meters",
        header=header_row,
        dtype=str,
    )

    df.columns = [clean_text(c) for c in df.columns]

    missing = [c for c in REQUIRED_METER_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns in Meters sheet: {missing}")

    df = df[REQUIRED_METER_COLUMNS].copy()

    df = df.dropna(
        subset=[
            "Property Name",
            "Portfolio Manager ID",
            "Portfolio Manager Meter ID",
            "Meter Name",
            "Meter Type",
        ]
    )

    df["live_property_id"] = df["Portfolio Manager ID"].apply(normalize_id)
    df["live_meter_id"] = df["Portfolio Manager Meter ID"].apply(normalize_id)
    df["building_name"] = df["Property Name"].apply(clean_text)
    df["meter_name"] = df["Meter Name"].apply(clean_text)
    df["meter_type"] = df["Meter Type"].apply(clean_text)
    df["unit"] = df["Units"].apply(clean_text)

    df["utility"] = df.apply(
        lambda r: classify_utility(r["meter_type"], r["meter_name"]),
        axis=1,
    )

    df["guessed_building_code"] = df.apply(
        lambda r: guess_building_code_from_name(r["building_name"])
        or guess_building_code_from_name(r["meter_name"]),
        axis=1,
    )

    df = df[
        [
            "guessed_building_code",
            "building_name",
            "utility",
            "live_property_id",
            "live_meter_id",
            "meter_name",
            "meter_type",
            "unit",
        ]
    ]

    # Keep only the utilities we are working on right now.
    df = df[df["utility"].isin(["Natural Gas", "Water", "Chilled Water"])]

    return df


def load_payment_matchup_needed_pairs():
    if not PAYMENT_EXTRACT_FILE.exists():
        raise FileNotFoundError(f"Missing file: {PAYMENT_EXTRACT_FILE}")

    df = pd.read_excel(PAYMENT_EXTRACT_FILE, dtype=str)

    df["building_code"] = df["building_code"].astype(str).str.strip().str.upper()
    df["utility"] = df["utility"].astype(str).str.strip()

    pairs = (
        df[["building_code", "utility"]]
        .drop_duplicates()
        .sort_values(["utility", "building_code"])
        .reset_index(drop=True)
    )

    return pairs


def build_manual_override_row(building_code, utility, portfolio_df, override):
    override_meter_name = override["meter_name"]

    possible = portfolio_df[
        (portfolio_df["meter_name"] == override_meter_name)
        & (portfolio_df["utility"] == utility)
    ]

    if len(possible) == 1:
        p = possible.iloc[0]

        return {
            "mapping_status": "MATCHED_MANUAL_OVERRIDE",
            "building_code": building_code,
            "building_name": p["building_name"],
            "utility": utility,
            "test_property_id": "",
            "test_meter_id": "",
            "live_property_id": p["live_property_id"],
            "live_meter_id": p["live_meter_id"],
            "unit": p["unit"],
            "meter_name": p["meter_name"],
            "meter_type": p["meter_type"],
            "review_notes": override["review_notes"],
        }

    return {
        "mapping_status": "MANUAL_OVERRIDE_FAILED",
        "building_code": building_code,
        "building_name": "",
        "utility": utility,
        "test_property_id": "",
        "test_meter_id": "",
        "live_property_id": "",
        "live_meter_id": "",
        "unit": "",
        "meter_name": override_meter_name,
        "meter_type": "",
        "review_notes": f"Manual override failed. Expected meter name not found exactly once: {override_meter_name}",
    }


def build_draft_mapping(portfolio_df, needed_pairs_df):
    rows = []

    for _, needed in needed_pairs_df.iterrows():
        building_code = clean_text(needed["building_code"]).upper()
        utility = clean_text(needed["utility"])

        override = MANUAL_MAPPING_OVERRIDES.get((building_code, utility))

        if override:
            rows.append(
                build_manual_override_row(
                    building_code=building_code,
                    utility=utility,
                    portfolio_df=portfolio_df,
                    override=override,
                )
            )
            continue

        possible = portfolio_df[
            (portfolio_df["guessed_building_code"] == building_code)
            & (portfolio_df["utility"] == utility)
        ]

        if len(possible) == 1:
            p = possible.iloc[0]

            rows.append(
                {
                    "mapping_status": "MATCHED",
                    "building_code": building_code,
                    "building_name": p["building_name"],
                    "utility": utility,
                    "test_property_id": "",
                    "test_meter_id": "",
                    "live_property_id": p["live_property_id"],
                    "live_meter_id": p["live_meter_id"],
                    "unit": p["unit"],
                    "meter_name": p["meter_name"],
                    "meter_type": p["meter_type"],
                    "review_notes": "",
                }
            )

        elif len(possible) > 1:
            for _, p in possible.iterrows():
                rows.append(
                    {
                        "mapping_status": "MULTIPLE_POSSIBLE_MATCHES",
                        "building_code": building_code,
                        "building_name": p["building_name"],
                        "utility": utility,
                        "test_property_id": "",
                        "test_meter_id": "",
                        "live_property_id": p["live_property_id"],
                        "live_meter_id": p["live_meter_id"],
                        "unit": p["unit"],
                        "meter_name": p["meter_name"],
                        "meter_type": p["meter_type"],
                        "review_notes": "Review duplicate possible matches",
                    }
                )

        else:
            rows.append(
                {
                    "mapping_status": "MISSING_MATCH",
                    "building_code": building_code,
                    "building_name": "",
                    "utility": utility,
                    "test_property_id": "",
                    "test_meter_id": "",
                    "live_property_id": "",
                    "live_meter_id": "",
                    "unit": "",
                    "meter_name": "",
                    "meter_type": "",
                    "review_notes": "No matching Portfolio meter found by building code + utility",
                }
            )

    return pd.DataFrame(rows)


def save_output(draft_df, portfolio_df, needed_pairs_df):
    OUTPUT_DIR.mkdir(exist_ok=True)

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        draft_df.to_excel(writer, sheet_name="Draft Mapping", index=False)
        portfolio_df.to_excel(writer, sheet_name="Portfolio Meters Filtered", index=False)
        needed_pairs_df.to_excel(writer, sheet_name="Needed From Payment Matchup", index=False)

    print("\nCreated:")
    print(OUTPUT_FILE)

    print("\nDraft mapping status summary:")
    print(draft_df["mapping_status"].value_counts(dropna=False))

    print("\nUtilities in Portfolio filtered:")
    print(portfolio_df["utility"].value_counts(dropna=False))

    print("\nNeeded pairs from Payment Matchup:")
    print(needed_pairs_df["utility"].value_counts(dropna=False))


def main():
    print("CSU ENERGY STAR - Generate Portfolio Meter Mapping Draft")
    print("-------------------------------------------------------")

    portfolio_df = load_portfolio_meters()
    needed_pairs_df = load_payment_matchup_needed_pairs()
    draft_df = build_draft_mapping(portfolio_df, needed_pairs_df)

    save_output(draft_df, portfolio_df, needed_pairs_df)

    print("\nDone. Draft only. Nothing uploaded.")


if __name__ == "__main__":
    main()