# Mattermost User Management Scripts

This directory contains Python scripts for managing Mattermost users and teams via the API.

## Setup

1.  **Environment**:
    Ensure you have a `.env` file in the project root (one level up) with `MM_URL` and `MM_TOKEN` (or `MM_ADMIN_USER`/`MM_ADMIN_PASS`).

2.  **Install Dependencies**:
    ```bash
    make setup
    ```

## Usage

### Import Users from CSV

Reads `users.csv` and creates/updates users.

**Logic:**
- **Team Column**: Treated as a **Channel Name**. The user is added to this channel (created if missing) within the `default_team`.
- **Tags Column**: Added to the user's **Position** field in Mattermost.
- **Default Team**: All users are added to the team defined in `config.yaml` (`default_team`).

**Dry Run:**
```bash
make import
```

**Execute:**
```bash
make import ARGS="--execute"
```

**Custom CSV:**
```bash
make import CSV="../my_users.csv" ARGS="--execute"
```

### Disable Users
Disables users listed in a CSV or text file. Defaults to `../disable.csv`.
The file should have an `email` column or list one email per line.

**Dry Run:**
```bash
make disable
```

**Execute:**
```bash
make disable ARGS="--execute"
```

**Custom File:**
```bash
make disable DISABLE_CSV="../leavers.csv" ARGS="--execute"
```

### Manual Usage
You can also run the scripts directly using the virtual environment python:

```bash
.venv/bin/python import_users.py --csv ../users.csv --dry-run
.venv/bin/python disable_users.py --file ../disable.csv --execute
```

## Testing

Run automated smoke tests:
```bash
make test
```
