from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "input" / "current_payment_matchup"
OUTPUT_DIR = BASE_DIR / "output"


SHEETS_TO_EXTRACT = {
    "Natural Gas": "Natural Gas",
    "Water": "Water",
    "Chilled Water": "Chilled Water",
}

REQUIRED_COLUMNS = [
    "Account Number",
    "Building Code",
    "Usage Period",
    "Bill Date",
    "Amount Approved",
    "Use",
]


def clean_date(value):
    """
    Convert Excel/Pandas date values into YYYY-MM-DD.
    Returns empty string if date is missing or invalid.
    """
    if pd.isna(value) or str(value).strip() == "":
        return ""

    parsed = pd.to_datetime(value, errors="coerce")

    if pd.isna(parsed):
        return ""

    return parsed.strftime("%Y-%m-%d")


def clean_account_number(value):
    """
    Convert account numbers like 79123600.0 into 79123600.
    Keeps text account numbers safely if conversion fails.
    """
    if pd.isna(value) or str(value).strip() == "":
        return ""

    try:
        return str(int(float(value)))
    except Exception:
        return str(value).strip()


def clean_text(value):
    """
    Clean text values and safely handle blanks.
    """
    if pd.isna(value):
        return ""

    return str(value).strip()


def clean_number(value):
    """
    Convert Excel values into float.
    Handles commas, dollar signs, blanks, and invalid text safely.
    """
    if pd.isna(value) or str(value).strip() == "":
        return None

    cleaned = str(value).replace(",", "").replace("$", "").strip()

    try:
        return float(cleaned)
    except Exception:
        return None


def normalize_columns(df):
    """
    Remove hidden spaces from column names.
    Example: 'Receipt ' becomes 'Receipt'
    """
    df.columns = [str(col).strip() for col in df.columns]
    return df


def find_payment_matchup_files():
    """
    Finds current/future Payment Matchup files inside:
    input/current_payment_matchup/
    """
    files = sorted(INPUT_DIR.glob("Payment Match Up FY *.xlsx"))
    return files


def find_sheet_name(file_path, target_sheet):
    """
    Finds sheet names even if Excel has hidden spaces.
    Example: 'Water ' still matches 'Water'
    """
    excel = pd.ExcelFile(file_path)
    target_clean = target_sheet.strip().lower()

    for sheet in excel.sheet_names:
        sheet_clean = sheet.strip().lower()
        if sheet_clean == target_clean:
            return sheet

    return None


def validate_columns(df, sheet_name, file_name):
    """
    Check if required columns exist.
    """
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]

    if missing:
        print(f"Skipping {file_name} / {sheet_name}. Missing columns: {missing}")
        print("Available columns:")
        for col in df.columns:
            print(f"  - {repr(col)}")
        return False

    return True


def first_day_next_month(date_value):
    """
    If this is the last available row for a building/utility,
    estimate the end date as the first day of the next month.
    """
    parsed = pd.to_datetime(date_value, errors="coerce")

    if pd.isna(parsed):
        return ""

    next_month = parsed + pd.DateOffset(months=1)
    next_month_first_day = pd.Timestamp(
        year=next_month.year,
        month=next_month.month,
        day=1,
    )

    return next_month_first_day.strftime("%Y-%m-%d")


def fix_non_overlapping_end_dates(records):
    """
    Fix ENERGY STAR overlap warnings.

    Old logic:
        end_date = Bill Date

    New safer logic:
        end_date = next start_date for the same building + utility + account number

    If there is no next row:
        end_date = first day of the next month

    bill_date is still preserved separately.
    """
    if not records:
        return records

    df = pd.DataFrame(records)

    df["start_dt"] = pd.to_datetime(df["start_date"], errors="coerce")

    group_cols = ["building_code", "utility", "account_number"]

    df = df.sort_values(group_cols + ["start_dt"])

    df["next_start_dt"] = df.groupby(group_cols)["start_dt"].shift(-1)

    fixed_end_dates = []

    for _, row in df.iterrows():
        next_start = row["next_start_dt"]

        if pd.notna(next_start):
            fixed_end_dates.append(next_start.strftime("%Y-%m-%d"))
        else:
            fixed_end_dates.append(first_day_next_month(row["start_date"]))

    df["end_date"] = fixed_end_dates

    df["date_logic"] = "end_date calculated from next Usage Period to prevent overlap"

    df = df.drop(columns=["start_dt", "next_start_dt"])

    return df.to_dict("records")


def extract_sheet(file_path, sheet_name, utility):
    """
    Extract one utility sheet from one Payment Matchup workbook.
    """
    print(f"Reading {file_path.name} / {sheet_name}")

    df = pd.read_excel(file_path, sheet_name=sheet_name, header=0)
    df = normalize_columns(df)

    if not validate_columns(df, sheet_name, file_path.name):
        return []

    # Keep rows that have the core data needed for upload/review.
    df = df.dropna(
        subset=[
            "Account Number",
            "Building Code",
            "Usage Period",
            "Bill Date",
            "Amount Approved",
            "Use",
        ]
    )

    df["Building Code"] = df["Building Code"].astype(str).str.strip().str.upper()

    # Present/future business rule:
    # Chilled Water from Payment Matchup should only include TA.
    if utility == "Chilled Water":
        df = df[df["Building Code"] == "TA"]

    records = []

    for index, row in df.iterrows():
        usage = clean_number(row.get("Use"))
        cost = clean_number(row.get("Amount Approved"))

        # Skip rows with invalid usage/cost.
        if usage is None or cost is None:
            continue

        start_date = clean_date(row.get("Usage Period"))
        bill_date = clean_date(row.get("Bill Date"))

        # Skip rows with missing start date.
        if not start_date:
            continue

        record = {
            "source_file": file_path.name,
            "source_sheet": sheet_name,
            "source_row_number": index + 2,
            "utility": utility,
            "account_number": clean_account_number(row.get("Account Number")),
            "building_code": clean_text(row.get("Building Code")).upper(),
            "start_date": start_date,
            "end_date": "",  # calculated later to prevent overlap
            "bill_date": bill_date,
            "usage": usage,
            "cost": cost,
            "receipt": clean_text(row.get("Receipt", "")),
            "invoice": clean_text(row.get("Invoice", "")),
            "payment_date": clean_date(row.get("Payment Date", "")),
            "entered_by": clean_text(row.get("Name", "")),
            "comments": clean_text(row.get("Comments", "")),
            "ready_to_upload": False,
            "validation_notes": "Extracted only. Meter mapping not applied yet.",
        }

        records.append(record)

    return records


def extract_current_payment_matchups():
    """
    Extract Natural Gas, Water, and TA Chilled Water
    from current/future Payment Matchup files.
    """
    all_records = []
    files = find_payment_matchup_files()

    if not files:
        print(f"No Payment Matchup files found in: {INPUT_DIR}")
        return []

    for file_path in files:
        print(f"\nProcessing file: {file_path.name}")

        for target_sheet_name, utility in SHEETS_TO_EXTRACT.items():
            actual_sheet_name = find_sheet_name(file_path, target_sheet_name)

            if actual_sheet_name is None:
                print(f"Sheet not found, skipping: {file_path.name} / {target_sheet_name}")
                continue

            try:
                records = extract_sheet(file_path, actual_sheet_name, utility)
                all_records.extend(records)
            except Exception as e:
                print(f"Error reading {file_path.name} / {actual_sheet_name}: {e}")

    all_records = fix_non_overlapping_end_dates(all_records)

    return all_records


def save_output(records):
    """
    Save extracted records to Excel review file.
    """
    OUTPUT_DIR.mkdir(exist_ok=True)

    output_file = OUTPUT_DIR / "current_payment_matchup_extract.xlsx"

    df = pd.DataFrame(records)

    df.to_excel(output_file, index=False)

    print("\nCreated:")
    print(output_file)

    print("\nSummary:")
    if not df.empty:
        print(df.groupby(["source_file", "utility"]).size())
    else:
        print("No records extracted.")

    print("\nDate logic:")
    if not df.empty and "date_logic" in df.columns:
        print(df["date_logic"].value_counts())

    return output_file


def main():
    print("CSU ENERGY STAR - Current/Future Payment Matchup Extract")
    print("--------------------------------------------------------")

    records = extract_current_payment_matchups()

    print(f"\nTotal records extracted: {len(records)}")

    save_output(records)

    print("\nDone. Extract only. Nothing uploaded.")


if __name__ == "__main__":
    main()