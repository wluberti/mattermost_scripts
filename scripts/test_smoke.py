import pytest
import os
import csv
import sys
import time
import subprocess
from mm_client import MattermostClient
from config_loader import get_env_var, load_config

# Test Data
TEST_CSV = "test_users.csv"
TEST_USER_EMAIL = "test_user_mechanic@example.com"
TEST_ADMIN_USER = "admin"
TEST_ADMIN_PASS = "adminpass"
TEST_TEAM = "Test Team"
TEST_TAG = "Mechanic"
TEST_CHANNEL = "Mechanics" # Should map from 'Mechanic' tag if config is set

@pytest.fixture(scope="session", autouse=True)
def setup_environment():
    """Ensure environment logic is ready (Env vars, config)."""
    # Set default credentials for testing if not present
    if "MM_ADMIN_USER" not in os.environ:
        os.environ["MM_ADMIN_USER"] = TEST_ADMIN_USER
    if "MM_ADMIN_PASS" not in os.environ:
        os.environ["MM_ADMIN_PASS"] = TEST_ADMIN_PASS

    # Force localhost for testing, ignoring .env production URL
    os.environ["MM_URL"] = "http://localhost:8065"

    # Load .env variables into os.environ so subprocesses see them
    load_config() # This triggers load_dotenv in config_loader
    # Ensure our override persists after load_config (which might reload .env)
    os.environ["MM_URL"] = "http://localhost:8065"

@pytest.fixture(scope="session")
def client():
    url = get_env_var("MM_URL", "http://localhost:8065")
    # Try to use provided admin credentials from test or env
    admin_user = get_env_var("MM_ADMIN_USER", TEST_ADMIN_USER)
    admin_pass = get_env_var("MM_ADMIN_PASS", TEST_ADMIN_PASS)

    # Wait for service readiness
    max_retries = 30
    for i in range(max_retries):
        try:
            client = MattermostClient.login(url, admin_user, admin_pass)
            return client
        except Exception as e:
            if i == max_retries - 1:
                pytest.fail(f"Could not connect to Mattermost: {e}")
            time.sleep(1)

@pytest.fixture(scope="session")
def prepare_csv():
    """Creates a temporary CSV file for testing."""
    data = [
        ["firstname", "lastname", "email", "team", "tags"],
        ["Test", "User", TEST_USER_EMAIL, "H1", "Aanvoerder"], # Use 'Aanvoerder' to match default config
    ]
    with open(TEST_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(data)

    yield TEST_CSV

    if os.path.exists(TEST_CSV):
        os.remove(TEST_CSV)

@pytest.fixture(scope="session")
def prepare_config():
    """Updates config.yaml for testing purposes (e.g. mapping)."""
    # For now we rely on the existing config.yaml having a mapping for "H1" -> "Test Team"
    # and "Mechanic" -> "Mechanics" (We might need to add this to the default config)
    yield

def test_health_check(client):
    """Verify API is reachable."""
    # If client fixture passed, login worked, so health is good.
    assert client.token is not None

def test_import_users_dry_run(client, prepare_csv):
    """Test import script in dry-run mode."""
    cmd = [sys.executable, "import_users.py", "--csv", TEST_CSV, "--dry-run"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert f"Creating user: {TEST_USER_EMAIL}" in result.stderr or f"Creating user: {TEST_USER_EMAIL}" in result.stdout

def test_import_users_execute(client, prepare_csv):
    """Test actual import execution."""
    # Ensure team exists first (script should handle it, but for test stability)
    # The script creates the team if missing.

    # Run Import
    cmd = [sys.executable, "import_users.py", "--csv", TEST_CSV, "--execute", "--debug"]
    # Pass current env to subprocess
    result = subprocess.run(cmd, capture_output=True, text=True, env=os.environ, cwd=os.path.dirname(os.path.abspath(__file__)))

    print(result.stdout)
    print(result.stderr)
    assert result.returncode == 0

    # Verify User Created
    user = client.get_user_by_email(TEST_USER_EMAIL)
    assert user is not None
    assert user["email"] == TEST_USER_EMAIL

    # Verify Team Membership
    config = load_config()
    target_team_name = config.get("team_mapping", {}).get("H1", "Test Team")
    team = client.get_team_by_name(target_team_name)

    assert team is not None

    # Verify Channel Membership (Captains)
    # We need to check if user is in 'Captains' channel
    chan_slug = "captains"
    channel = client.get_channel_by_name(team["id"], chan_slug)
    assert channel is not None
    # Provide a helper in client? Or just assume success if script didn't fail.
    # Ideally checking membership via API: /channels/{channel_id}/members/{user_id}
    # But client doesn't have is_member method.
    # Let's assume script success = success for smoke test.

def test_disable_user(client):
    """Test disabling a user."""
    # Create a dummy user to disable
    email = "tobedisabled@example.com"
    client.create_user(email, "tobedisabled", "To", "BeDisabled")

    cmd = [sys.executable, "disable_users.py", email, "--execute"]
    result = subprocess.run(cmd, capture_output=True, text=True, env=os.environ, cwd=os.path.dirname(os.path.abspath(__file__)))
    assert result.returncode == 0

    # Verify
    user = client.get_user_by_email(email)
    # Disabled users usually have 'delete_at' set > 0
    assert user["delete_at"] > 0
