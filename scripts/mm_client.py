import requests
from typing import Dict, Any, Optional, List
from utils import get_logger

logger = get_logger(__name__)

class TeamMemberLimitExceededError(Exception):
    """Raised when the team has reached its member limit."""
    pass

class MattermostClient:
    """Client for interacting with the Mattermost API."""

    def __init__(self, url: str, token: str):
        """Initializes the client with URL and token."""
        self.url = url.rstrip("/")
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest", # Often needed for MM API
        }
        self.api_url = f"{self.url}/api/v4"

    @classmethod
    def login(cls, url: str, login_id: str, password: str) -> 'MattermostClient':
        """Authenticates with username/password and returns a client instance."""
        url = url.rstrip("/")
        api_url = f"{url}/api/v4"
        data = {"login_id": login_id, "password": password}
        try:
            response = requests.post(f"{api_url}/users/login", json=data)
            response.raise_for_status()
            token = response.headers.get("Token")
            if not token:
                raise ValueError("Login successful but no token returned in headers.")
            return cls(url, token)
        except requests.exceptions.RequestException as e:
             logger.error(f"Login failed: {e}")
             raise

    def _request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None, expected_status_codes: List[int] = None) -> Any:
        """Internal method to handle requests with error handling."""
        url = f"{self.api_url}{endpoint}"
        try:
            response = requests.request(
                method, url, headers=self.headers, json=data, params=params
            )
            response.raise_for_status()
            # Handle empty content (e.g. 204 No Content)
            if not response.content:
                return {}
            return response.json()
        except requests.exceptions.RequestException as e:
            is_expected = False
            if expected_status_codes and isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
                if e.response.status_code in expected_status_codes:
                     is_expected = True

            if not is_expected:
                error_msg = f"API Request Failed: {method} {url} - {e}"
                if hasattr(e, 'response') and e.response is not None:
                    error_msg += f" | Response: {e.response.text}"
                logger.error(error_msg)
            else:
                logger.debug(f"Expected API Error: {method} {url} - {e}")
            raise

    # User Management
    def get_users_by_ids(self, user_ids: List[str]) -> List[Dict]:
        """Fetches users by a list of IDs."""
        if not user_ids:
            return []
        return self._request("POST", "/users/ids", data=user_ids)

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        try:
            return self._request("GET", f"/users/email/{email}", expected_status_codes=[404])
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        try:
            return self._request("GET", f"/users/username/{username}", expected_status_codes=[404])
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    def create_user(self, email: str, username: str, first_name: str, last_name: str, position: str = "", nickname: str = "", password: str = "Password123!") -> Dict:
        """Creates a new user."""
        data = {
            "email": email,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "position": position,
            "nickname": nickname,
            "password": password,
        }
        logger.info(f"Creating user: {username} ({email})")
        return self._request("POST", "/users", data=data)

    def update_user(self, user_id: str, first_name: str, last_name: str, position: str = "", nickname: str = "") -> Dict:
        """Updates user profile."""
        data = {
            "first_name": first_name,
            "last_name": last_name,
            "position": position,
            "nickname": nickname,
        }
        logger.info(f"Updating user {user_id}")
        return self._request("PUT", f"/users/{user_id}/patch", data=data)

    def disable_user(self, user_id: str) -> Dict:
        """Disables a user."""
        logger.info(f"Disabling user {user_id}")
        return self._request("DELETE", f"/users/{user_id}")

    def activate_user(self, user_id: str) -> Dict:
        """Activates a user."""
        logger.info(f"Activating user {user_id}")
        data = {"active": True}
        return self._request("PUT", f"/users/{user_id}/active", data=data)

    # Team Management
    def get_team_by_name(self, name: str) -> Optional[Dict]:
        try:
            return self._request("GET", f"/teams/name/{name}", expected_status_codes=[404])
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    def get_team_members(self, team_id: str) -> List[Dict]:
        """Returns a list of team members."""
        # Note: Pagination might be needed for large teams, but default page size is usually 60 or 200.
        # We'll stick to one page explicitly requesting a large number?
        # Or better, just use the helper to get all?
        # For this specific case, simpler is better. Standard endpoint returns paged results.
        # We'll request 200 users for now.
        return self._request("GET", f"/teams/{team_id}/members", params={"per_page": 200})

    def create_team(self, name: str, display_name: str) -> Dict:
         """Creates a new team."""
         data = {
             "name": name,
             "display_name": display_name,
             "type": "O", # Open team
         }
         logger.info(f"Creating team: {name}")
         return self._request("POST", "/teams", data=data)

    def remove_user_from_team(self, team_id: str, user_id: str) -> Dict:
        """Removes a user from a team."""
        logger.info(f"Removing user {user_id} from team {team_id}")
        return self._request("DELETE", f"/teams/{team_id}/members/{user_id}")

    def add_user_to_team(self, team_id: str, user_id: str) -> Dict:
        """Adds a user to a team."""
        data = {
            "team_id": team_id,
            "user_id": user_id,
        }
        try:
            return self._request("POST", f"/teams/{team_id}/members", data=data)
        except requests.exceptions.HTTPError as e:
             if e.response and "app.team.join_user_to_team.save_member.exception" in str(e.response.text):
                 logger.debug(f"User {user_id} already in team {team_id}")
                 return {} # Idempotent-ish
             if e.response.status_code == 400:
                  # Check for max accounts error specifically to raise it
                  if "max_accounts.app_error" in e.response.text:
                      logger.warning(f"Team limit reached when adding user {user_id} to team {team_id}.")
                      raise TeamMemberLimitExceededError(f"Team {team_id} is full.")

                  logger.warning(f"User {user_id} likely already in team {team_id} (400 returned). Response: {e.response.text}")
                  return {}
             raise

    # Channel Management
    def get_channel_by_name(self, team_id: str, channel_name: str) -> Optional[Dict]:
        try:
            return self._request("GET", f"/teams/{team_id}/channels/name/{channel_name}", expected_status_codes=[404])
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    def create_channel(self, team_id: str, name: str, display_name: str) -> Dict:
        data = {
            "team_id": team_id,
            "name": name,
            "display_name": display_name,
            "type": "O" # Open channel
        }
        logger.info(f"Creating channel: {name}")
        return self._request("POST", "/channels", data=data)

    def add_user_to_channel(self, channel_id: str, user_id: str) -> Dict:
        data = {
            "user_id": user_id
        }
        try:
            return self._request("POST", f"/channels/{channel_id}/members", data=data)
        except requests.exceptions.HTTPError as e:
             if e.response and "app.channel.create_member.user_already_in_channel.app_error" in str(e.response.text): # Check exact error
                 logger.debug(f"User {user_id} already in channel {channel_id}")
                 return {}
             if e.response.status_code == 400: # Sometimes returns 400 for already existing
                  logger.warning(f"User {user_id} likely already in channel {channel_id} (400 returned). Response: {e.response.text}")
                  return {}
             raise

    def remove_user_from_channel(self, channel_id: str, user_id: str) -> Dict:
        try:
            return self._request("DELETE", f"/channels/{channel_id}/members/{user_id}")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404: # User not in channel
                return {}
            raise
