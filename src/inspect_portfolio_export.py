from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
PORTFOLIO_FILE = BASE_DIR / "input" / "My-Portfolio.xlsx"


def main():
    print("CSU ENERGY STAR - Inspect My Portfolio Export")
    print("---------------------------------------------")

    if not PORTFOLIO_FILE.exists():
        print(f"File not found: {PORTFOLIO_FILE}")
        return

    excel = pd.ExcelFile(PORTFOLIO_FILE)

    print("\nSheets found:")
    for sheet in excel.sheet_names:
        print(f"- {repr(sheet)}")

    print("\nColumn preview by sheet:")

    for sheet in excel.sheet_names:
        print(f"\n--- {sheet} ---")

        try:
            df = pd.read_excel(PORTFOLIO_FILE, sheet_name=sheet, nrows=5)

            print("Columns:")
            for col in df.columns:
                print(f"  - {repr(col)}")

            print("\nFirst 5 rows:")
            print(df.head().to_string())

        except Exception as e:
            print(f"Could not read sheet {sheet}: {e}")


if __name__ == "__main__":
    main()