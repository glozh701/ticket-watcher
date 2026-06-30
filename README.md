# Aichi-Nagoya 2026 Ticket Watcher

Monitors 9/28 Honor of Kings / ELS08.

Target:

- `idProduct`: `452`
- `sessionCode`: `ELS08`
- Detail URL: `https://generalsale.tickets-aichi-nagoya2026.org/showProduct.html?idProduct=452`

## Setup

1. Create a new GitHub repo.
2. Upload these files.
3. Go to **Settings -> Secrets and variables -> Actions -> New repository secret**.
4. Add email secrets.

For Gmail, use an App Password, not your normal password.

Required secrets:

```text
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_gmail_app_password
NOTIFY_TO=your_email@gmail.com
NOTIFY_FROM=your_email@gmail.com
```

5. Go to **Actions**, enable workflows if prompted.
6. Run **Watch Aichi-Nagoya Ticket -> Run workflow** once manually.

It then runs every 5 minutes.

## Notification logic

It emails you only when status becomes:

- `BUY`
- `LIMITED`

It does not notify repeatedly if the status stays the same.
