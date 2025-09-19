#! /usr/bin/env python3
import csv
import re
import time
import secrets
import string
import smtplib
import requests
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

# ========================
# Load .env
# ========================
load_dotenv()

MATTERMOST_URL = os.getenv("MM_URL", "").rstrip("/")
API_TOKEN      = os.getenv("MM_TOKEN", "")
TEAM_NAME      = os.getenv("MM_TEAM", "")

EXPORT_FILE    = os.getenv("EXPORT_FILE", "export.csv")
RATE_LIMIT_DELAY = float(os.getenv("RATE_LIMIT_DELAY", "0.2"))

SMTP_SERVER = os.getenv("SMTP_SERVER", "")
SMTP_PORT   = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER   = os.getenv("SMTP_USER", "")
SMTP_PASS   = os.getenv("SMTP_PASS", "")
EMAIL_FROM  = os.getenv("EMAIL_FROM", "")

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json",
}

# ========================
# Helpers
# ========================
def generate_password(length=12):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    return "".join(secrets.choice(alphabet) for _ in range(length))

def send_welcome_email(to_email, username, password):
    body = f"""Hallo,

Je Mattermost account is aangemaakt voor {MATTERMOST_URL}

Inloggegevens:
- Gebruikersnaam: {username}
- Wachtwoord: {password}

Log in op: {MATTERMOST_URL}

Je kunt het wachtwoord na inloggen wijzigen.

Groeten,
Volleybalvereniging De Spuyt
"""
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = "Welkom bij Mattermost - De Spuyt"
    msg["From"] = EMAIL_FROM
    msg["To"] = to_email

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
    print(f"📧 Sent welcome email to {to_email}")

def slugify_username(firstname, tussenvoegsel, lastname):
    parts = [firstname, tussenvoegsel, lastname]
    parts = [p.strip().lower() for p in parts if p and str(p).strip()]
    return ".".join(parts)

def slugify_channel_name(label: str) -> str:
    return re.sub(r"[^a-z0-9-]", "-", label.strip().lower())

def get_team_id(team_name_or_slug: str) -> str:
    slug = slugify_channel_name(team_name_or_slug)
    r = requests.get(f"{MATTERMOST_URL}/api/v4/teams/name/{slug}", headers=HEADERS)
    if r.status_code == 200:
        return r.json()["id"]

    # fallback: search through visible teams
    page, per_page = 0, 200
    while True:
        rr = requests.get(f"{MATTERMOST_URL}/api/v4/teams?page={page}&per_page={per_page}", headers=HEADERS)
        if rr.status_code != 200:
            break
        teams = rr.json()
        if not teams:
            break
        for t in teams:
            if t.get("display_name", "").strip().lower() == team_name_or_slug.strip().lower():
                return t["id"]
            if t.get("name", "").strip().lower() == team_name_or_slug.strip().lower():
                return t["id"]
        if len(teams) < per_page:
            break
        page += 1

    raise RuntimeError(f"Team '{team_name_or_slug}' not found.")

def get_or_create_channel(team_id: str, label: str) -> str | None:
    slug = slugify_channel_name(label)
    r = requests.get(f"{MATTERMOST_URL}/api/v4/teams/{team_id}/channels/name/{slug}", headers=HEADERS)
    if r.status_code == 200:
        return r.json()["id"]

    payload = {
        "team_id": team_id,
        "name": slug,
        "display_name": label.strip(),
        "type": "O",
    }
    r = requests.post(f"{MATTERMOST_URL}/api/v4/channels", headers=HEADERS, json=payload)
    if r.status_code == 201:
        ch_id = r.json()["id"]
        print(f"Created channel '{label}' (slug '{slug}')")
        return ch_id
    print(f"Failed to create channel {label}: {r.status_code} {r.text}")
    return None

def add_user_to_channel(user_id: str, channel_id: str):
    r = requests.post(
        f"{MATTERMOST_URL}/api/v4/channels/{channel_id}/members",
        headers=HEADERS, json={"user_id": user_id}
    )
    if r.status_code in (200, 201):
        print(f"  → Added user {user_id} to channel {channel_id}")
    elif r.status_code == 400 and "exists" in r.text:
        print(f"  → Already in channel {channel_id}")
    else:
        print(f"  → Failed to add user to channel {channel_id}: {r.status_code} {r.text}")

# ========================
# Main
# ========================
def main():
    team_id = get_team_id(TEAM_NAME)
    print(f"Using team '{TEAM_NAME}' → {team_id}")

    with open(EXPORT_FILE, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            firstname = (row.get("Voornaam") or "").strip()
            tussenvoegsel = (row.get("Tussenvoegsel") or "").strip()
            lastname = (row.get("Achternaam") or "").strip()
            email = (row.get("E-mailadres voor contact") or "").strip()
            labels = (row.get("Labels") or "")

            if not firstname or not lastname or not email:
                print("Skipping row (missing essential data):", row)
                continue

            username = slugify_username(firstname, tussenvoegsel, lastname)
            password = generate_password()

            # Create user
            user_payload = {
                "username": username,
                "email": email,
                "password": password,
                "first_name": firstname,
                "last_name": f"{tussenvoegsel} {lastname}".strip(),
            }
            r = requests.post(f"{MATTERMOST_URL}/api/v4/users", headers=HEADERS, json=user_payload)

            if r.status_code == 201:
                user_id = r.json()["id"]
                print(f"Created user {username} ({email})")

                if labels:
                    for label in re.split(r"[,\^]", labels):
                        label = label.strip()
                        if not label:
                            continue
                        ch_id = get_or_create_channel(team_id, label)
                        if ch_id:
                            add_user_to_channel(user_id, ch_id)

                try:
                    send_welcome_email(email, username, password)
                except Exception as e:
                    print(f"⚠️ Email send failed for {email}: {e}")

            elif r.status_code == 400 and "is already taken" in r.text:
                print(f"User {username} already exists, skipping creation")
            else:
                print(f"Failed to create {username}: {r.status_code} {r.text}")

            time.sleep(RATE_LIMIT_DELAY)

if __name__ == "__main__":
    main()

