from pathlib import Path
import os
import requests
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"


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
        raise ValueError("For now, ESPM_ENV must be test.")

    if allow_live != "false":
        raise ValueError("ALLOW_LIVE_UPLOAD must stay false.")

    if not username or not password:
        raise ValueError("Missing ESPM_USERNAME or ESPM_PASSWORD in config/settings.env")

    return username, password, base_url


def test_connection():
    username, password, base_url = load_settings()

    meter_id = "25965184"
    url = base_url.rstrip("/") + f"/meter/{meter_id}"

    print("Testing ENERGY STAR Test API connection...")
    print(f"URL: {url}")
    print(f"Username: {username}")
    print("Password: hidden")

    response = requests.get(
        url,
        auth=(username, password),
        headers={"Accept": "application/xml"},
        timeout=30,
    )

    print("\nStatus Code:", response.status_code)
    print("\nResponse Preview:")
    print(response.text[:1000])

    if response.status_code in [200, 201]:
        print("\nSUCCESS: Test API connection works.")
    elif response.status_code == 401:
        print("\nFAILED: Username/password not accepted.")
    elif response.status_code == 403:
        print("\nFAILED: Account exists, but permission/access may be blocked.")
    elif response.status_code == 404:
        print("\nFAILED: Endpoint not found. The base URL or endpoint may need adjustment.")
    else:
        print("\nFAILED or unexpected response. Review status code and response.")


if __name__ == "__main__":
    test_connection()