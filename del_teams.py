#!/usr/bin/env python3
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

def hard_delete_team(team_identifier):
    """
    Permanently delete a team and everything under it from Mattermost DB.
    team_identifier can be the team name (slug) or display_name.
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

    # Find team
    cur.execute(
        "SELECT Id, Name, DisplayName FROM Teams WHERE Name = %s OR DisplayName = %s",
        (team_identifier, team_identifier)
    )
    row = cur.fetchone()
    if not row:
        print(f"Team '{team_identifier}' not found.")
        return

    team_id, team_name, team_display = row
    print(f"Found team → ID={team_id}, Name={team_name}, DisplayName={team_display}")

    # First get all channels in this team
    cur.execute("SELECT Id, Name FROM Channels WHERE TeamId = %s", (team_id,))
    channels = cur.fetchall()

    for channel_id, channel_name in channels:
        print(f"  Deleting channel {channel_name} ({channel_id})")

        # Delete channel memberships
        cur.execute("DELETE FROM ChannelMembers WHERE ChannelId = %s", (channel_id,))

        # Delete posts in this channel
        cur.execute("DELETE FROM Posts WHERE ChannelId = %s", (channel_id,))

        # Delete reactions belonging to posts
        cur.execute(
            "DELETE FROM Reactions WHERE PostId IN (SELECT Id FROM Posts WHERE ChannelId = %s)",
            (channel_id,)
        )

        # Delete files belonging to posts
        cur.execute(
            "DELETE FROM FileInfo WHERE PostId IN (SELECT Id FROM Posts WHERE ChannelId = %s)",
            (channel_id,)
        )

        # Finally delete the channel itself
        cur.execute("DELETE FROM Channels WHERE Id = %s", (channel_id,))

    # Delete team memberships
    cur.execute("DELETE FROM TeamMembers WHERE TeamId = %s", (team_id,))

    # Finally delete the team itself
    cur.execute("DELETE FROM Teams WHERE Id = %s", (team_id,))
    print(f"✅ Deleted team {team_name} ({team_display}) and all related data.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: ./delete_team.py <team-name-or-display-name>")
        sys.exit(1)

    identifier = sys.argv[1].strip()
    hard_delete_team(identifier)

