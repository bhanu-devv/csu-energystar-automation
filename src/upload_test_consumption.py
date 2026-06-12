from pathlib import Path
import os
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

from upload_log import write_upload_log


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
OUTPUT_DIR = BASE_DIR / "output"


def load_settings():
    env_file = CONFIG_DIR / "settings.env"

    if not env_file.exists():
        raise FileNotFoundError(f"Missing settings file: {env_file}")

    load_dotenv(env_file)

    username = os.getenv("ESPM_USERNAME")
    password = os.getenv("ESPM_PASSWORD")
    base_url = os.getenv("ESPM_TEST_BASE_URL")
    env = os.getenv("ESPM_ENV", "test")
    allow_live = os.getenv("ALLOW_LIVE_UPLOAD", "false").lower()

    if env != "test":
        raise ValueError("Blocked: ESPM_ENV must be test.")

    if allow_live != "false":
        raise ValueError("Blocked: ALLOW_LIVE_UPLOAD must stay false.")

    if not username or not password:
        raise ValueError("Missing ESPM_USERNAME or ESPM_PASSWORD in config/settings.env")

    return username, password, base_url


def read_existing_consumption(meter_id):
    username, password, base_url = load_settings()

    url = base_url.rstrip("/") + f"/meter/{meter_id}/consumptionData"

    print("\nChecking existing meter entries...")
    print(f"URL: {url}")

    response = requests.get(
        url,
        auth=(username, password),
        headers={"Accept": "application/xml"},
        timeout=30,
    )

    print("Existing entries check status:", response.status_code)

    if response.status_code != 200:
        print("Could not read existing entries. Response:")
        print(response.text)
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
        print("Could not parse existing consumption XML.")
        print(e)

    print(f"Existing entries found: {len(existing_entries)}")

    return existing_entries


def already_exists(existing_entries, start_date, end_date):
    for entry in existing_entries:
        existing_start = entry.get("startDate")
        existing_end = entry.get("endDate")

        if existing_start == start_date and existing_end == end_date:
            return True

    return False


def upload_consumption_xml(meter_id, xml_file):
    username, password, base_url = load_settings()

    record = {
        "building_code": "TA",
        "building_name": "Theater Arts",
        "utility": "Chilled Water",
        "test_meter_id": meter_id,
        "start_date": "2026-03-01",
        "end_date": "2026-04-02",
        "usage": 24946.0,
        "cost": 10113.11,
    }

    existing_entries = read_existing_consumption(meter_id)

    if already_exists(existing_entries, record["start_date"], record["end_date"]):
        message = "Skipped: entry already exists for this start/end date."
        print("\nDUPLICATE BLOCKED")
        print(message)

        write_upload_log(
            record,
            "SKIPPED",
            message,
            "DUPLICATE_BLOCKED"
        )
        return

    url = base_url.rstrip("/") + f"/meter/{meter_id}/consumptionData"

    if not xml_file.exists():
        raise FileNotFoundError(f"Missing XML file: {xml_file}")

    xml_text = xml_file.read_text(encoding="utf-8")

    print("\nENERGY STAR TEST UPLOAD")
    print("-----------------------")
    print(f"URL: {url}")
    print(f"Meter ID: {meter_id}")
    print(f"XML File: {xml_file}")
    print("Username:", username)
    print("Password: hidden")
    print("\nXML being sent:")
    print(xml_text)

    confirm = input("\nType UPLOAD_TEST to send this to ENERGY STAR Test Environment: ")

    if confirm.strip() != "UPLOAD_TEST":
        print("Upload cancelled. Nothing was sent.")
        return

    response = requests.post(
        url,
        auth=(username, password),
        headers={
            "Content-Type": "application/xml",
            "Accept": "application/xml",
        },
        data=xml_text.encode("utf-8"),
        timeout=30,
    )

    print("\nStatus Code:", response.status_code)
    print("\nResponse:")
    print(response.text)

    if response.status_code in [200, 201]:
        print("\nSUCCESS: Consumption data uploaded to ENERGY STAR Test Environment.")
        write_upload_log(record, response.status_code, response.text, "SUCCESS")
    else:
        print("\nFAILED: Upload did not succeed. Review response above.")
        write_upload_log(record, response.status_code, response.text, "FAILED")


def main():
    meter_id = "25965184"

    xml_file = OUTPUT_DIR / "xml_dry_run" / "TA_Chilled_Water_2026-03_meter_25965184.xml"

    upload_consumption_xml(meter_id, xml_file)


if __name__ == "__main__":
    main()