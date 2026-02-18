# Mattermost User Management Toolkit

A set of Python scripts to manage Mattermost users via the API, including bulk import from CSV, disabling users, and managing channel membership.

## Prerequisites

- **Python 3.10+**
- **Docker & Docker Compose** (for local development/testing)
- A running Mattermost instance (local or production)

## Setup

1.  Navigate to the scripts directory:
    ```bash
    cd scripts/mm_user_mgmt
    ```

2.  Set up the Python environment:
    ```bash
    make setup
    ```

3.  Configure the environment:
    - Ensure `.env` exists in the project root with `MM_URL`.
    - Retrieve an Admin Token from Mattermost (System Console > Integrations > Bot Accounts or Personal Access Token).
    - Add `MM_TOKEN=your_token_here` to `.env`.
    - Alternatively, set `MM_ADMIN_USER` and `MM_ADMIN_PASS` in `.env` for username/password authentication (less secure, not recommended for production).

4.  Review and update `config.yaml`:
    - Map CSV `team` values to Mattermost Team names.
    - Map CSV `tags` to Mattermost Channels.
    - Set default channels.

## Usage

### Import Users from CSV

Reads `users.csv` (headers: `firstname,lastname,email,team,tags`) and creates/updates users.

```bash
# Dry Run (Preview changes)
./.venv/bin/python import_users.py --csv ../../users.csv --dry-run

# Execute Changes
./.venv/bin/python import_users.py --csv ../../users.csv --execute
```

### Disable Users

Disables users by email.

```bash
# Disable specific users
./.venv/bin/python disable_users.py user1@example.com user2@example.com --execute

# Disable from file (one email per line)
./.venv/bin/python disable_users.py --file list_of_leavers.txt --execute
```

### Manage Channel Membership

Add or remove a user from a specific channel.

```bash
./.venv/bin/python channel_mgmt.py --email user@example.com --team "My Team" --channel "Town Square" --action add --execute
```

## Testing

Run the automated smoke tests (requires Docker):

```bash
make test
```

## Production Deployment

1.  Clone the repository to the production server.
2.  Ensure `.env` is configured with production `MM_URL` and a valid `MM_TOKEN`.
3.  Run `make setup` to install dependencies.
4.  Run the desired scripts using the `.venv/bin/python` interpreter.

## Project Structure

- `import_users.py`: Main import script.
- `disable_users.py`: User disabling script.
- `channel_mgmt.py`: Single user channel management.
- `mm_client.py`: Mattermost API client library.
- `config.yaml`: Configuration for teams/channels.
- `test_smoke.py`: Automated tests.
