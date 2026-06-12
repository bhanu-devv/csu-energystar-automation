from pathlib import Path
import os
import requests
import pandas as pd
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from upload_log import write_upload_log


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
OUTPUT_DIR = BASE_DIR / "output"

SETTINGS_FILE = CONFIG_DIR / "settings.env"
READY_FILE = OUTPUT_DIR / "current_payment_matchup_ready.xlsx"


def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def clean_number(value):
    if pd.isna(value) or str(value).strip() == "":
        return None

    try:
        return float(str(value).replace(",", "").replace("$", "").strip())
    except Exception:
        return None


def load_settings():
    if not SETTINGS_FILE.exists():
        raise FileNotFoundError(f"Missing settings file: {SETTINGS_FILE}")

    load_dotenv(SETTINGS_FILE)

    esp_env = os.getenv("ESPM_ENV", "test").strip().lower()
    allow_live_upload = os.getenv("ALLOW_LIVE_UPLOAD", "false").strip().lower()

    username = os.getenv("ESPM_USERNAME")
    password = os.getenv("ESPM_PASSWORD")

    test_base_url = os.getenv("ESPM_TEST_BASE_URL")
    live_base_url = os.getenv("ESPM_LIVE_BASE_URL")

    if esp_env not in ["test", "live"]:
        raise ValueError("ESPM_ENV must be either test or live.")

    if allow_live_upload not in ["true", "false"]:
        raise ValueError("ALLOW_LIVE_UPLOAD must be true or false.")

    if esp_env == "live" and allow_live_upload != "true":
        raise ValueError("Blocked: ESPM_ENV=live but ALLOW_LIVE_UPLOAD is not true.")

    if not username or not password:
        raise ValueError("Missing ESPM_USERNAME or ESPM_PASSWORD in settings.env")

    if esp_env == "test":
        base_url = test_base_url
    else:
        base_url = live_base_url

    if not base_url:
        raise ValueError("Missing ENERGY STAR base URL in settings.env")

    return {
        "esp_env": esp_env,
        "allow_live_upload": allow_live_upload,
        "username": username,
        "password": password,
        "base_url": base_url.rstrip("/"),
    }


def load_ready_rows():
    if not READY_FILE.exists():
        raise FileNotFoundError(f"Missing ready file: {READY_FILE}")

    df = pd.read_excel(READY_FILE, dtype=str)

    if "ready_to_upload" not in df.columns:
        raise ValueError("Missing ready_to_upload column. Run apply_meter_mapping.py first.")

    ready_df = df[df["ready_to_upload"].astype(str).str.lower() == "true"].copy()

    return ready_df


def get_meter_id(row, esp_env):
    if esp_env == "test":
        return clean_text(row.get("test_meter_id"))
    return clean_text(row.get("live_meter_id"))


def read_existing_consumption(settings, meter_id):
    url = f"{settings['base_url']}/meter/{meter_id}/consumptionData"

    response = requests.get(
        url,
        auth=(settings["username"], settings["password"]),
        headers={"Accept": "application/xml"},
        timeout=30,
    )

    if response.status_code != 200:
        print(f"Could not read existing entries for meter {meter_id}. Status: {response.status_code}")
        print(response.text[:1000])
        return []

    existing_entries = []

    try:
        root = ET.fromstring(response.text)

        for item in root.iter():
            if item.tag.endswith("meterConsumption"):
                entry = {}

                for child in item:
                    tag = child.tag.split("}")[-1]
                    entry[tag] = child.text

                if entry:
                    existing_entries.append(entry)

    except Exception as e:
        print(f"Could not parse existing consumption XML for meter {meter_id}: {e}")

    return existing_entries


def already_exists(existing_entries, start_date, end_date):
    for entry in existing_entries:
        if entry.get("startDate") == start_date and entry.get("endDate") == end_date:
            return True

    return False


def build_consumption_xml(row):
    usage = clean_number(row.get("usage"))
    cost = clean_number(row.get("cost"))

    if usage is None:
        raise ValueError("Invalid usage")

    if cost is None:
        raise ValueError("Invalid cost")

    start_date = clean_text(row.get("start_date"))
    end_date = clean_text(row.get("end_date"))

    if not start_date or not end_date:
        raise ValueError("Missing start_date or end_date")

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<meterData>
  <meterConsumption estimatedValue="false">
    <usage>{usage}</usage>
    <startDate>{start_date}</startDate>
    <endDate>{end_date}</endDate>
    <cost>{cost}</cost>
  </meterConsumption>
</meterData>
"""

    return xml


def upload_one_row(settings, row):
    esp_env = settings["esp_env"]
    meter_id = get_meter_id(row, esp_env)

    record = {
        "building_code": clean_text(row.get("building_code")),
        "building_name": clean_text(row.get("building_name")),
        "utility": clean_text(row.get("utility")),
        "test_meter_id": clean_text(row.get("test_meter_id")),
        "live_meter_id": clean_text(row.get("live_meter_id")),
        "start_date": clean_text(row.get("start_date")),
        "end_date": clean_text(row.get("end_date")),
        "usage": clean_text(row.get("usage")),
        "cost": clean_text(row.get("cost")),
    }

    if not meter_id:
        message = f"Skipped: missing {esp_env} meter ID."
        print(message)
        write_upload_log(record, "SKIPPED", message, "MISSING_METER_ID")
        return "SKIPPED"

    existing_entries = read_existing_consumption(settings, meter_id)

    if already_exists(existing_entries, record["start_date"], record["end_date"]):
        message = "Skipped: entry already exists for this start/end date."
        print(f"Duplicate blocked: {record['building_code']} {record['utility']} {record['start_date']} to {record['end_date']}")
        write_upload_log(record, "SKIPPED", message, "DUPLICATE_BLOCKED")
        return "DUPLICATE_BLOCKED"

    xml_text = build_consumption_xml(row)

    url = f"{settings['base_url']}/meter/{meter_id}/consumptionData"

    response = requests.post(
        url,
        auth=(settings["username"], settings["password"]),
        headers={"Content-Type": "application/xml", "Accept": "application/xml"},
        data=xml_text.encode("utf-8"),
        timeout=30,
    )

    if response.status_code in [200, 201]:
        print(f"Uploaded: {record['building_code']} {record['utility']} {record['start_date']} to {record['end_date']}")
        write_upload_log(record, response.status_code, response.text, "SUCCESS")
        return "SUCCESS"

    print(f"Failed: {record['building_code']} {record['utility']} {record['start_date']} to {record['end_date']}")
    print("Status:", response.status_code)
    print(response.text[:1000])
    write_upload_log(record, response.status_code, response.text, "FAILED")
    return "FAILED"


def main():
    print("CSU ENERGY STAR - Upload Ready Rows")
    print("-----------------------------------")

    settings = load_settings()
    ready_df = load_ready_rows()

    print(f"\nEnvironment: {settings['esp_env']}")
    print(f"Base URL: {settings['base_url']}")
    print(f"Ready rows found: {len(ready_df)}")

    if ready_df.empty:
        print("\nNo rows ready to upload.")
        return

    print("\nRows that will be uploaded:")
    print(
        ready_df[
            [
                "building_code",
                "utility",
                "start_date",
                "end_date",
                "usage",
                "cost",
                "test_meter_id",
                "live_meter_id",
            ]
        ].to_string(index=False)
    )

    confirm = input("\nType UPLOAD_READY_TEST to upload these rows to ENERGY STAR Test: ")

    if settings["esp_env"] == "test":
        if confirm.strip() != "UPLOAD_READY_TEST":
            print("Upload cancelled. Nothing was sent.")
            return
    else:
        print("Live upload is not supported by this confirmation phrase.")
        print("Upload cancelled.")
        return

    results = []

    for _, row in ready_df.iterrows():
        result = upload_one_row(settings, row)
        results.append(result)

    print("\nUpload result summary:")
    print(pd.Series(results).value_counts())


if __name__ == "__main__":
    main()