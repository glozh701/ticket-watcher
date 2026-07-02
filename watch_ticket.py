import os
import sys
import json
import time
import smtplib
import urllib.parse
import urllib.request
import urllib.error
from email.message import EmailMessage
from datetime import datetime, timezone

PRODUCT_ID = int(os.getenv("PRODUCT_ID", "452"))
SESSION_CODE = os.getenv("SESSION_CODE", "ELS08")
TARGET_STATUS_NOTIFY = {"BUY", "LIMITED"}

API_URL = os.getenv(
    "API_URL",
    "https://generalsale.tickets-aichi-nagoya2026.org/getFilteredProductsJSON.th?"
    + urllib.parse.urlencode({
        "nohistory": "true",
        "eventCategoryFather": "3",
        "eventCategoryList": "44,43,36,17,5,55,30,23,50,6,45,8,26,21,51,56,48,13,57,11",
        "eventDateList": "2026/09/28",
        "eventVenueList": "45,30,25,52,13,55,19,34,60,62,15,40,50,16,41,26,49,22,57,47,27",
        "currentPage": "1",
        "rowsNumber": "100",
    }),
)

DETAIL_URL = f"https://generalsale.tickets-aichi-nagoya2026.org/showProduct.html?idProduct={PRODUCT_ID}"
STATE_FILE = os.getenv("STATE_FILE", "last_status.json")

# Retry configuration
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY = int(os.getenv("RETRY_DELAY", "5"))  # seconds between retries

# Realistic browser headers to reduce chance of being blocked
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Accept-Encoding": "identity",
    "Referer": "https://generalsale.tickets-aichi-nagoya2026.org/",
    "Origin": "https://generalsale.tickets-aichi-nagoya2026.org",
    "Connection": "keep-alive",
}


def fetch_products():
    """Fetch product data with retries. Returns data dict or None on failure."""
    req = urllib.request.Request(API_URL, headers=REQUEST_HEADERS)

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code == 403:
                print(f"[attempt {attempt}/{MAX_RETRIES}] HTTP 403 Forbidden - site may be blocking this IP")
            elif e.code >= 500:
                print(f"[attempt {attempt}/{MAX_RETRIES}] HTTP {e.code} server error")
            else:
                print(f"[attempt {attempt}/{MAX_RETRIES}] HTTP {e.code}: {e.reason}")
                # Don't retry on 4xx (except 403) — likely a permanent issue
                if e.code != 429:
                    break
        except urllib.error.URLError as e:
            last_error = e
            print(f"[attempt {attempt}/{MAX_RETRIES}] Network error: {e.reason}")
        except Exception as e:
            last_error = e
            print(f"[attempt {attempt}/{MAX_RETRIES}] Unexpected error: {e}")

        if attempt < MAX_RETRIES:
            delay = RETRY_DELAY * attempt  # simple linear backoff
            print(f"  Retrying in {delay}s...")
            time.sleep(delay)

    print(f"All {MAX_RETRIES} attempts failed. Last error: {last_error}")
    return None


def find_target(data):
    for p in data.get("products", []):
        if int(p.get("idProduct", -1)) == PRODUCT_ID or p.get("sessionCode") == SESSION_CODE:
            return p
    return None


def load_last_status():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("status")
    except FileNotFoundError:
        return None


def save_status(status):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"status": status, "checked_at": datetime.now(timezone.utc).isoformat()}, f)


def send_email(subject, body):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    notify_to = os.getenv("NOTIFY_TO")
    notify_from = os.getenv("NOTIFY_FROM", smtp_user)

    if not all([smtp_host, smtp_user, smtp_pass, notify_to, notify_from]):
        print("Email not configured. Skipping email notification.")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = notify_from
    msg["To"] = notify_to
    msg.set_content(body)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")


def notify(product, previous_status):
    status = product.get("availabilityStatus", "UNKNOWN")
    subject = f"🎟️ Ticket status changed: {SESSION_CODE} is {status}"
    body = f"""Ticket status changed!

Product: {product.get("nmProduct")}
Info: {product.get("nmInfo")}
Status: {status}
Previous status: {previous_status}
Date: {product.get("dhStart")}
Venue: {product.get("nmVenue")}
URL: {DETAIL_URL}

Checked at: {datetime.now(timezone.utc).isoformat()}
"""
    print(body)
    send_email(subject, body)


def main():
    now = datetime.now(timezone.utc).isoformat()

    data = fetch_products()
    if data is None:
        # Graceful exit — don't fail the workflow for transient fetch errors
        print(f"{now} Fetch failed, will retry next run.")
        sys.exit(0)

    product = find_target(data)

    if not product:
        # Product not listed yet — not an error, just not available in results
        print(f"{now} Target not found: PRODUCT_ID={PRODUCT_ID}, SESSION_CODE={SESSION_CODE}")
        print("Product may not be on sale yet or filters don't match. Will check again next run.")
        save_status("NOT_FOUND")
        sys.exit(0)

    status = product.get("availabilityStatus", "UNKNOWN")
    previous_status = load_last_status()

    print(f"{now} {SESSION_CODE}/{PRODUCT_ID}: {status}")

    should_notify = status in TARGET_STATUS_NOTIFY and status != previous_status
    save_status(status)

    if should_notify:
        notify(product, previous_status)
    else:
        print("No notification needed.")


if __name__ == "__main__":
    main()
