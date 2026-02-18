import csv
import argparse
import sys
from typing import List, Dict
from config_loader import load_config, get_env_var
from mm_client import MattermostClient
from utils import setup_logging, get_logger, confirm_action

logger = get_logger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description="Import users from CSV to Mattermost.")
    parser.add_argument("--csv", required=True, help="Path to users.csv file")
    parser.add_argument("--dry-run", action="store_true", help="Simulate actions without changes")
    parser.add_argument("--execute", action="store_true", help="Commit changes (required if wet-run not enabled in config)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()

def process_row(row: Dict[str, str], config: Dict, client: MattermostClient, dry_run: bool):
    email = row.get("email", "").strip()
    firstname = row.get("firstname", "").strip()
    lastname = row.get("lastname", "").strip()
    team_csv = row.get("team", "").strip()
    tags = [t.strip() for t in row.get("tags", "").split(",") if t.strip()]

    if not email:
        logger.warning(f"Skipping row with missing email: {row}")
        return

    username = email.split("@")[0] # Simple username generation

    # 1. Create/Update User
    user = client.get_user_by_email(email)
    if user:
        logger.info(f"User exists: {email}")
        if not dry_run:
            client.update_user(user["id"], firstname, lastname)
    else:
        logger.info(f"Creating user: {email}")
        if not dry_run:
            user = client.create_user(email, username, firstname, lastname)
            if not user:
                logger.error(f"Failed to create user {email}")
                return

    if dry_run or not user:
        return

    user_id = user["id"]

    # 2. Determine Team
    # Check config mapping first, then CSV value, then default
    team_name_mapped = config.get("team_mapping", {}).get(team_csv)
    target_team_name = team_name_mapped or team_csv or config.get("default_team")

    if not target_team_name:
        logger.error(f"Could not determine team for {email}. CSV: '{team_csv}'")
        return

    # 3. Add to Team
    team = client.get_team_by_name(target_team_name)
    if not team:
        # Auto-create team if it doesn't exist? Constraint says "Create team if missing OR fail".
        # Let's try to create it if it's the mapped name, to be helpful.
        logger.info(f"Team '{target_team_name}' not found. Attempting to create...")
        if not dry_run:
            team = client.create_team(target_team_name.lower().replace(" ", "-"), target_team_name)

    if team:
        logger.info(f"Adding {email} to team '{target_team_name}'")
        if not dry_run:
            client.add_user_to_team(team["id"], user_id)

            # 4. Add to Default Channels
            for chan_name in config.get("default_channels", []):
                channel = client.get_channel_by_name(team["id"], chan_name.lower().replace(" ", "-"))
                if channel:
                     client.add_user_to_channel(channel["id"], user_id)
                else:
                    logger.warning(f"Default channel '{chan_name}' not found in team '{target_team_name}'")

            # 5. Add to Tag-based Channels
            tag_mapping = config.get("tag_channel_mapping", {})
            for tag in tags:
                if tag in tag_mapping:
                    channels_to_add = tag_mapping[tag]
                    for chan_name in channels_to_add:
                        # Normalize channel name for lookup (often slugified)
                        chan_slug = chan_name.lower().replace(" ", "-")
                        channel = client.get_channel_by_name(team["id"], chan_slug)
                        if not channel:
                             # Try creating
                             logger.info(f"Channel '{chan_name}' not found. Creating...")
                             if not dry_run:
                                 channel = client.create_channel(team["id"], chan_slug, chan_name)

                        if channel:
                            logger.info(f"Adding {email} to channel '{chan_name}' (Tag: {tag})")
                            if not dry_run:
                                client.add_user_to_channel(channel["id"], user_id)
                        else:
                            logger.error(f"Could not find or create channel '{chan_name}'")

    else:
        logger.error(f"Team '{target_team_name}' could not be found or created.")

def main():
    args = parse_args()
    setup_logging(args.debug)
    config = load_config()

    # Safety check
    if not args.dry_run and not args.execute and not config.get("enable_wet_run"):
        logger.error("Dry-run is implied. Use --execute to apply changes or set enable_wet_run in config.")
        args.dry_run = True

    # Auth
    try:
        url = get_env_var("MM_URL", required=True)
        # Try token first, then credentials
        token = get_env_var("MM_TOKEN")
        if not token:
            # Try login
            admin_user = get_env_var("MM_ADMIN_USER") # Optional in .env but needed if no token
            admin_pass = get_env_var("MM_ADMIN_PASS")
            if admin_user and admin_pass:
                logger.info("Authenticating via username/password...")
                client = MattermostClient.login(url, admin_user, admin_pass)
            else:
                logger.error("No MM_TOKEN provided and MM_ADMIN_USER/PASS missing.")
                sys.exit(1)
        else:
            client = MattermostClient(url, token)

    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        sys.exit(1)

    # Process CSV
    try:
        with open(args.csv, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                process_row(row, config, client, args.dry_run)
    except FileNotFoundError:
        logger.error(f"CSV file not found: {args.csv}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Error processing CSV: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
