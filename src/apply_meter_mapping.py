from pathlib import Path
import os
import pandas as pd
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
CONFIG_DIR = BASE_DIR / "config"

SETTINGS_FILE = CONFIG_DIR / "settings.env"


# Whole Payment Matchup mode:
# True  = process all extracted rows regardless of date
# False = only process rows on/after UPLOAD_START_DATE
PROCESS_WHOLE_PAYMENT_MATCHUP = True

UPLOAD_START_DATE = "2026-06-01"


def load_settings():
    if not SETTINGS_FILE.exists():
        raise FileNotFoundError(f"Missing settings file: {SETTINGS_FILE}")

    load_dotenv(SETTINGS_FILE)

    esp_env = os.getenv("ESPM_ENV", "test").strip().lower()
    allow_live_upload = os.getenv("ALLOW_LIVE_UPLOAD", "false").strip().lower()

    if esp_env not in ["test", "live"]:
        raise ValueError("ESPM_ENV must be either test or live.")

    if allow_live_upload not in ["true", "false"]:
        raise ValueError("ALLOW_LIVE_UPLOAD must be true or false.")

    return esp_env, allow_live_upload


def load_extract():
    extract_file = OUTPUT_DIR / "current_payment_matchup_extract.xlsx"

    if not extract_file.exists():
        raise FileNotFoundError(f"Missing extract file: {extract_file}")

    return pd.read_excel(extract_file, dtype=str)


def load_meter_mapping():
    mapping_file = CONFIG_DIR / "meter_mapping.csv"

    if not mapping_file.exists():
        raise FileNotFoundError(f"Missing meter mapping file: {mapping_file}")

    return pd.read_csv(mapping_file, dtype=str)


def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def apply_mapping(records_df, mapping_df, esp_env, allow_live_upload):
    records_df["building_code"] = records_df["building_code"].astype(str).str.strip().str.upper()
    records_df["utility"] = records_df["utility"].astype(str).str.strip()

    mapping_df["building_code"] = mapping_df["building_code"].astype(str).str.strip().str.upper()
    mapping_df["utility"] = mapping_df["utility"].astype(str).str.strip()

    output_rows = []
    upload_start = pd.to_datetime(UPLOAD_START_DATE)

    for _, row in records_df.iterrows():
        row_dict = row.to_dict()

        building_code = clean_text(row_dict.get("building_code")).upper()
        utility = clean_text(row_dict.get("utility"))
        start_date = pd.to_datetime(row_dict.get("start_date"), errors="coerce")

        match = mapping_df[
            (mapping_df["building_code"] == building_code)
            & (mapping_df["utility"] == utility)
        ]

        row_dict["test_property_id"] = ""
        row_dict["test_meter_id"] = ""
        row_dict["live_property_id"] = ""
        row_dict["live_meter_id"] = ""

        row_dict["test_ready"] = False
        row_dict["live_ready"] = False
        row_dict["ready_to_upload"] = False
        row_dict["upload_environment"] = esp_env

        notes = []

        if pd.isna(start_date):
            notes.append("Invalid start date")

        if not PROCESS_WHOLE_PAYMENT_MATCHUP:
            if not pd.isna(start_date) and start_date < upload_start:
                notes.append(f"Before upload start date {UPLOAD_START_DATE}")

        if match.empty:
            notes.append("Missing meter mapping")
        else:
            m = match.iloc[0]

            row_dict["test_property_id"] = clean_text(m.get("test_property_id"))
            row_dict["test_meter_id"] = clean_text(m.get("test_meter_id"))
            row_dict["live_property_id"] = clean_text(m.get("live_property_id"))
            row_dict["live_meter_id"] = clean_text(m.get("live_meter_id"))

            if row_dict["test_meter_id"]:
                row_dict["test_ready"] = True

            if row_dict["live_meter_id"]:
                row_dict["live_ready"] = True

        # Decide what is allowed to upload based on settings.env
        if notes:
            row_dict["ready_to_upload"] = False
            row_dict["validation_notes"] = "; ".join(notes)

        else:
            if esp_env == "test":
                if row_dict["test_ready"]:
                    row_dict["ready_to_upload"] = True
                    row_dict["validation_notes"] = "Ready for ENERGY STAR test upload"
                else:
                    row_dict["ready_to_upload"] = False
                    row_dict["validation_notes"] = "Live mapped, but missing test meter ID"

            elif esp_env == "live":
                if allow_live_upload != "true":
                    row_dict["ready_to_upload"] = False
                    row_dict["validation_notes"] = "Live mapped, but live upload is blocked by ALLOW_LIVE_UPLOAD=false"
                elif row_dict["live_ready"]:
                    row_dict["ready_to_upload"] = True
                    row_dict["validation_notes"] = "Ready for ENERGY STAR live upload"
                else:
                    row_dict["ready_to_upload"] = False
                    row_dict["validation_notes"] = "Missing live meter ID"

        output_rows.append(row_dict)

    return pd.DataFrame(output_rows)


def save_ready_file(df):
    output_file = OUTPUT_DIR / "current_payment_matchup_ready.xlsx"

    df.to_excel(output_file, index=False)

    print("\nCreated:")
    print(output_file)

    print("\nMode:")
    if PROCESS_WHOLE_PAYMENT_MATCHUP:
        print("Processing whole Payment Matchup file")
    else:
        print(f"Processing only rows on/after {UPLOAD_START_DATE}")

    print("\nEnvironment:")
    print(df["upload_environment"].value_counts(dropna=False))

    print("\nTest-ready summary:")
    print(df["test_ready"].value_counts(dropna=False))

    print("\nLive-ready summary:")
    print(df["live_ready"].value_counts(dropna=False))

    print("\nReady to upload summary:")
    print(df["ready_to_upload"].value_counts(dropna=False))

    print("\nValidation notes summary:")
    print(df["validation_notes"].value_counts().head(30))

    print("\nReady rows by utility:")
    ready_df = df[df["ready_to_upload"] == True]
    if not ready_df.empty:
        print(ready_df.groupby(["utility"]).size())
    else:
        print("No ready rows yet.")

    print("\nLive-ready rows by utility:")
    live_ready_df = df[df["live_ready"] == True]
    if not live_ready_df.empty:
        print(live_ready_df.groupby(["utility"]).size())
    else:
        print("No live-ready rows yet.")

    return output_file


def main():
    print("CSU ENERGY STAR - Apply Meter Mapping")
    print("-------------------------------------")

    esp_env, allow_live_upload = load_settings()

    records_df = load_extract()
    mapping_df = load_meter_mapping()

    ready_df = apply_mapping(
        records_df=records_df,
        mapping_df=mapping_df,
        esp_env=esp_env,
        allow_live_upload=allow_live_upload,
    )

    save_ready_file(ready_df)

    print("\nDone. Mapping applied. Nothing uploaded.")


if __name__ == "__main__":
    main()