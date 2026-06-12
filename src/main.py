from pathlib import Path
import pandas as pd
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom


BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
CONFIG_DIR = BASE_DIR / "config"


def load_meter_mapping():
    mapping_file = CONFIG_DIR / "meter_mapping.csv"
    df = pd.read_csv(mapping_file, dtype=str)
    return df


def clean_date(value):
    if pd.isna(value):
        return None
    return pd.to_datetime(value).strftime("%Y-%m-%d")


def clean_account_number(value):
    if pd.isna(value):
        return ""
    try:
        return str(int(float(value)))
    except Exception:
        return str(value).strip()


def extract_ta_chilled_water(month="2026-03"):
    payment_file = INPUT_DIR / "Payment Match Up FY 2026.xlsx"

    print("Reading Chilled Water sheet...")

    df = pd.read_excel(payment_file, sheet_name="Chilled Water", header=0)

    df = df[df["Building Code"].astype(str).str.strip().str.upper() == "TA"]

    df = df.dropna(subset=["Usage Period", "Bill Date", "Amount Approved", "Use"])

    df["Usage Period Clean"] = pd.to_datetime(df["Usage Period"]).dt.strftime("%Y-%m")

    df = df[df["Usage Period Clean"] == month]

    records = []

    for _, row in df.iterrows():
        record = {
            "month": month,
            "building_code": "TA",
            "building_name": "Theater Arts",
            "utility": "Chilled Water",
            "account_number": clean_account_number(row["Account Number"]),
            "start_date": clean_date(row["Usage Period"]),
            "end_date": clean_date(row["Bill Date"]),
            "bill_date": clean_date(row["Bill Date"]),
            "usage": float(row["Use"]),
            "cost": float(row["Amount Approved"]),
            "unit": "ton hours",
            "source_file": "Payment Match Up FY 2026.xlsx",
            "source_sheet": "Chilled Water",
            "receipt": str(row.get("Receipt", "")).strip(),
            "invoice": str(row.get("Invoice", "")).strip(),
            "payment_date": clean_date(row.get("Payment Date", None)),
        }
        records.append(record)

    return records


def attach_meter_ids(records, mapping):
    output = []

    for record in records:
        match = mapping[
            (mapping["building_code"].str.upper() == record["building_code"].upper())
            & (mapping["utility"].str.upper() == record["utility"].upper())
        ]

        if match.empty:
            record["test_property_id"] = ""
            record["test_meter_id"] = ""
            record["live_property_id"] = ""
            record["live_meter_id"] = ""
            record["ready_to_upload"] = False
            record["validation_notes"] = "Missing meter mapping"
        else:
            m = match.iloc[0]
            record["test_property_id"] = m.get("test_property_id", "")
            record["test_meter_id"] = m.get("test_meter_id", "")
            record["live_property_id"] = m.get("live_property_id", "")
            record["live_meter_id"] = m.get("live_meter_id", "")

            if not record["test_meter_id"] or str(record["test_meter_id"]).lower() == "nan":
                record["ready_to_upload"] = False
                record["validation_notes"] = "Missing test meter ID"
            else:
                record["ready_to_upload"] = True
                record["validation_notes"] = "Ready for ENERGY STAR test upload"

        output.append(record)

    return output


def create_energy_star_xml(record):
    """
    Creates ENERGY STAR Portfolio Manager meter consumption XML.
    This is dry-run only. It does not upload.
    Correct API format:
    <meterData>
        <meterConsumption>
            ...
        </meterConsumption>
    </meterData>
    """

    meter_data = Element("meterData")

    meter_consumption = SubElement(meter_data, "meterConsumption")
    meter_consumption.set("estimatedValue", "false")

    usage = SubElement(meter_consumption, "usage")
    usage.text = str(record["usage"])

    start_date = SubElement(meter_consumption, "startDate")
    start_date.text = record["start_date"]

    end_date = SubElement(meter_consumption, "endDate")
    end_date.text = record["end_date"]

    cost = SubElement(meter_consumption, "cost")
    cost.text = str(record["cost"])

    raw_xml = tostring(meter_data, encoding="utf-8")
    pretty_xml = minidom.parseString(raw_xml).toprettyxml(indent="  ")

    return pretty_xml

def create_review_file(records, month):
    OUTPUT_DIR.mkdir(exist_ok=True)

    output_file = OUTPUT_DIR / f"TA_Chilled_Water_Upload_Review_{month}.xlsx"

    df = pd.DataFrame(records)
    df.to_excel(output_file, index=False)

    print(f"\nCreated review file:")
    print(output_file)

    return output_file


def create_xml_files(records, month):
    xml_dir = OUTPUT_DIR / "xml_dry_run"
    xml_dir.mkdir(exist_ok=True)

    for record in records:
        if not record["ready_to_upload"]:
            print("Skipping XML because record is not ready.")
            continue

        xml_text = create_energy_star_xml(record)

        xml_file = xml_dir / f"{record['building_code']}_{record['utility'].replace(' ', '_')}_{month}_meter_{record['test_meter_id']}.xml"

        with open(xml_file, "w", encoding="utf-8") as f:
            f.write(xml_text)

        print(f"\nCreated XML dry-run file:")
        print(xml_file)

        print("\nXML Preview:")
        print(xml_text)


def main():
    month = "2026-03"

    print("CSU ENERGY STAR Automation - XML Dry Run")
    print("----------------------------------------")

    mapping = load_meter_mapping()

    records = extract_ta_chilled_water(month)

    print(f"\nRecords extracted: {len(records)}")

    records = attach_meter_ids(records, mapping)

    for record in records:
        print("\nExtracted Record:")
        for key, value in record.items():
            print(f"{key}: {value}")

    create_review_file(records, month)

    create_xml_files(records, month)

    print("\nDone. Nothing uploaded. XML dry-run only.")


if __name__ == "__main__":
    main()