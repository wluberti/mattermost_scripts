import argparse
import sys
from config_loader import get_env_var
from mm_client import MattermostClient
from utils import setup_logging, get_logger, confirm_action

logger = get_logger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description="Disable Mattermost users.")
    parser.add_argument("emails", nargs="*", help="List of emails to disable")
    parser.add_argument("--file", help="File containing list of emails (one per line)")
    parser.add_argument("--execute", action="store_true", help="Apply changes")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()

def main():
    args = parse_args()
    setup_logging(args.debug)

    emails = args.emails
    if args.file:
        try:
            with open(args.file, "r") as f:
                emails.extend([line.strip() for line in f if line.strip()])
        except FileNotFoundError:
            logger.error(f"File not found: {args.file}")
            sys.exit(1)

    if not emails:
        logger.error("No emails provided.")
        sys.exit(1)

    if not args.execute:
        logger.info(f"Dry-run: Would disable {len(emails)} users: {', '.join(emails)}")
        logger.info("Use --execute to apply.")
        return

    # Auth
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

    for email in emails:
        user = client.get_user_by_email(email)
        if user:
            logger.info(f"Disabling {email} (ID: {user['id']})")
            client.disable_user(user["id"])
        else:
            logger.warning(f"User not found: {email}")

if __name__ == "__main__":
    main()
