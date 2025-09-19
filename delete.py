#! /usr/bin/env python3

import psycopg2
import sys
from dotenv import load_dotenv
import os

# ========================
# Load .env
# ========================
load_dotenv()

# === CONFIGURE THIS ===
DB_HOST = os.getenv(DB_HOST, "localhost")
DB_PORT = os.getenv(DB_PORT, 5432)
DB_NAME = os.getenv(DB_NAME, "")
DB_USER = os.getenv(DB_USER, "")
DB_PASS = os.getenv(DB_PASS, "")

def table_exists(cur, table_name):
    """Check if a table exists in the public schema."""
    cur.execute("""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = %s
        )
    """, (table_name.lower(),))
    return cur.fetchone()[0]


def hard_delete_user(identifier):
    """
    Permanently delete a user from Mattermost DB based on username or email.
    """
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    conn.autocommit = True
    cur = conn.cursor()

    # Find user by username or email
    cur.execute(
        "SELECT Id, Username, Email FROM Users WHERE Username = %s OR Email = %s",
        (identifier, identifier)
    )
    row = cur.fetchone()
    if not row:
        print(f"User '{identifier}' not found.")
        return

    user_id, username, email = row
    print(f"Found user → ID={user_id}, Username={username}, Email={email}")

    # Table → column mapping (adjusted for Mattermost schema differences)
    delete_targets = {
        "ChannelMembers": "UserId",
        "TeamMembers": "UserId",
        "Sessions": "UserId",
        "Preferences": "UserId",
        "Status": "UserId",
        "Audits": "UserId",           # sometimes CreatorId instead
        "UserAccessTokens": "UserId",
        "GroupMembers": "UserId",     # replaces UserGroups in newer versions
        "Posts": "UserId",
        "Reactions": "UserId",
        "FileInfo": "CreatorId"       # FileInfo uses CreatorId
    }

    for table, column in delete_targets.items():
        if table_exists(cur, table):
            try:
                cur.execute(f"DELETE FROM {table} WHERE {column} = %s", (user_id,))
                print(f"Deleted from {table}")
            except Exception as e:
                print(f"⚠️ Failed deleting from {table} ({column}): {e}")
        else:
            print(f"Skipped {table} (does not exist)")

    # Finally delete the user
    cur.execute("DELETE FROM Users WHERE Id = %s", (user_id,))
    print("Deleted user record.")

    cur.close()
    conn.close()
    print(f"✅ Hard delete complete for {identifier}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: ./delete.py <username-or-email>")
        sys.exit(1)

    identifier = sys.argv[1].strip()
    hard_delete_user(identifier)
