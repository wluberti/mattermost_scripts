import argparse
import sys
from config_loader import get_env_var
from mm_client import MattermostClient
from utils import setup_logging, get_logger

logger = get_logger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description="Manage channel membership.")
    parser.add_argument("--email", required=True, help="User email")
    parser.add_argument("--team", required=True, help="Team name")
    parser.add_argument("--channel", required=True, help="Channel name")
    parser.add_argument("--action", choices=["add", "remove"], required=True, help="Action to perform")
    parser.add_argument("--execute", action="store_true", help="Apply changes")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()

def main():
    args = parse_args()
    setup_logging(args.debug)

    if not args.execute:
        logger.info(f"Dry-run: Would {args.action} {args.email} to/from {args.team}/{args.channel}")
        return

    try:
        url = get_env_var("MM_URL", required=True)
        token = get_env_var("MM_TOKEN")
        if not token:
             admin_user = get_env_var("MM_ADMIN_USER")
             admin_pass = get_env_var("MM_ADMIN_PASS")
             if admin_user and admin_pass:
                 client = MattermostClient.login(url, admin_user, admin_pass)
             else:
                 logger.error("MM_TOKEN or Credentials required.")
                 sys.exit(1)
        else:
            client = MattermostClient(url, token)
    except Exception as e:
        logger.error(f"Auth failed: {e}")
        sys.exit(1)

    user = client.get_user_by_email(args.email)
    if not user:
        logger.error(f"User not found: {args.email}")
        sys.exit(1)

    team = client.get_team_by_name(args.team)
    if not team:
        logger.error(f"Team not found: {args.team}")
        sys.exit(1)

    # Normalize channel name
    chan_slug = args.channel.lower().replace(" ", "-")
    channel = client.get_channel_by_name(team["id"], chan_slug)
    if not channel:
        logger.error(f"Channel not found: {args.channel} (slug: {chan_slug})")
        sys.exit(1)

    if args.action == "add":
        logger.info(f"Adding {args.email} to {args.channel}")
        client.add_user_to_channel(channel["id"], user["id"])
        import re
        if re.match(r"^[A-Za-z]\d?$", args.channel):
            logger.info(f"Setting channel admin roles for {args.email} in '{args.channel}'")
            client.set_channel_member_roles(channel["id"], user["id"], "channel_user channel_admin")
    elif args.action == "remove":
        logger.info(f"Removing {args.email} from {args.channel}")
        client.remove_user_from_channel(channel["id"], user["id"])

if __name__ == "__main__":
    main()
