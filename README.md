# Mattermost User Management & Setup

This repository contains the Docker configuration for running a Mattermost instance and Python scripts for managing users and teams.

## Directory Structure

- `docker/`: Contains persistent data and configuration for Docker containers.
  - `db/`: Postgres database data.
  - `config/`: Mattermost configuration files.
  - `data/`: Mattermost file storage.
  - `logs/`: Mattermost logs.
  - `plugins/`: Mattermost plugins.
  - `web/cert/`: Nginx certificates.
- `scripts/`: Python scripts for user/team management and automation.
- `.env`: Environment variables for Docker and scripts.
- `docker-compose.yaml`: Docker service definition.
- `users.csv`: Source file for user imports.

## Setup

1.  **Environment Variables**:
    Copy `.env.example` to `.env` (if not already done) and configure the variables.
    ```bash
    cp .env.example .env
    ```
    Ensure `MM_ADMIN_USER` and `MM_ADMIN_PASS` are set if you plan to use the automation scripts without a hardcoded token.

2.  **Docker**:
    Start the services:
    ```bash
    docker compose up -d
    ```

3.  **Python Scripts**:
    Navigate to the `scripts/` directory and set up the environment:
    ```bash
    cd scripts
    make setup
    ```

## Usage

### User Import
To import users from `users.csv` (located in the root):
```bash
cd scripts
make import
```
To run with execution enabled:
```bash
make import ARGS="--execute"
```
To specify a different CSV file:
```bash
make import CSV="../other_users.csv" ARGS="--execute"
```

### Disabling Users
Prepare a `disable.csv` file in the root directory with a list of emails (one per line or in a CSV column named `email`).

To dry-run:
```bash
make disable
```

To execute:
```bash
make disable ARGS="--execute"
```

To specify a different file:
```bash
```bash
make disable DISABLE_CSV="../other_list.csv" ARGS="--execute"
```

## Maintenance
- **Logs**: Check `docker/logs/` or run `docker compose logs -f`.
- **Backups**: Ensure the `docker/` directory is backed up.
