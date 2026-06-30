import os
import sys
import json
import smtplib
import urllib.parse
import urllib.request
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
    })
)

DETAIL_URL = f"https://generalsale.tickets-aichi-nagoya2026.org/showProduct.html?idProduct={PRODUCT_ID}"
STATE_FILE = os.getenv("STATE_FILE", "last_status.json")


def fetch_products():
    req = urllib.request.Request(
        API_URL,
        headers={
            "User-Agent": "Mozilla/5.0 ticket-status-checker",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


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

    with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)


def notify(product, previous_status):
    status = product.get("availabilityStatus", "UNKNOWN")
    subject = f"Ticket status changed: {SESSION_CODE} is {status}"
    body = f"""Ticket status changed.

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
    data = fetch_products()
    product = find_target(data)

    if not product:
        print(f"Target not found: PRODUCT_ID={PRODUCT_ID}, SESSION_CODE={SESSION_CODE}")
        sys.exit(2)

    status = product.get("availabilityStatus", "UNKNOWN")
    previous_status = load_last_status()

    print(f"{datetime.now(timezone.utc).isoformat()} {SESSION_CODE}/{PRODUCT_ID}: {status}")

    should_notify = status in TARGET_STATUS_NOTIFY and status != previous_status
    save_status(status)

    if should_notify:
        notify(product, previous_status)
    else:
        print("No notification needed.")


if __name__ == "__main__":
    main()
