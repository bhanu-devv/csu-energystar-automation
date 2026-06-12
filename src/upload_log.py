from pathlib import Path
from datetime import datetime
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
LOG_FILE = OUTPUT_DIR / "upload_log.csv"


def write_upload_log(record, status_code, response_text, upload_status):
    OUTPUT_DIR.mkdir(exist_ok=True)

    log_row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "environment": "test",
        "building_code": record.get("building_code"),
        "building_name": record.get("building_name"),
        "utility": record.get("utility"),
        "meter_id": record.get("test_meter_id"),
        "start_date": record.get("start_date"),
        "end_date": record.get("end_date"),
        "usage": record.get("usage"),
        "cost": record.get("cost"),
        "status_code": status_code,
        "upload_status": upload_status,
        "response": response_text[:500],
    }

    if LOG_FILE.exists():
        df = pd.read_csv(LOG_FILE)
        df = pd.concat([df, pd.DataFrame([log_row])], ignore_index=True)
    else:
        df = pd.DataFrame([log_row])

    df.to_csv(LOG_FILE, index=False)

    print(f"Upload log updated: {LOG_FILE}")