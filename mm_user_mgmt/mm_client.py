import requests
import json
import time
from typing import Dict, Any, List, Optional
from utils import get_logger

logger = get_logger(__name__)

class MattermostClient:
    def __init__(self, url: str, token: str):
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

    def _request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Any:
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
            logger.error(f"API Request Failed: {method} {url} - {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.debug(f"Response: {e.response.text}")
            raise

    # User Management
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        try:
            return self._request("GET", f"/users/email/{email}")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    def create_user(self, email: str, username: str, first_name: str, last_name: str, password: str = "Password123!") -> Dict:
        """Creates a new user."""
        data = {
            "email": email,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "password": password,
        }
        logger.info(f"Creating user: {username} ({email})")
        return self._request("POST", "/users", data=data)

    def update_user(self, user_id: str, first_name: str, last_name: str) -> Dict:
        """Updates user profile."""
        data = {
            "first_name": first_name,
            "last_name": last_name,
        }
        logger.info(f"Updating user {user_id}")
        return self._request("PUT", f"/users/{user_id}/patch", data=data)

    def disable_user(self, user_id: str) -> Dict:
        """Disables a user."""
        logger.info(f"Disabling user {user_id}")
        return self._request("DELETE", f"/users/{user_id}")

    # Team Management
    def get_team_by_name(self, name: str) -> Optional[Dict]:
        try:
            return self._request("GET", f"/teams/name/{name}")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    def create_team(self, name: str, display_name: str) -> Dict:
         """Creates a new team."""
         data = {
             "name": name,
             "display_name": display_name,
             "type": "O", # Open team
         }
         logger.info(f"Creating team: {name}")
         return self._request("POST", "/teams", data=data)

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
             # Sometimes 400 is returned for already exists
             if e.response.status_code == 400:
                  logger.debug(f"User {user_id} likely already in team {team_id} (400 returned)")
                  return {}
             raise

    # Channel Management
    def get_channel_by_name(self, team_id: str, channel_name: str) -> Optional[Dict]:
        try:
            return self._request("GET", f"/teams/{team_id}/channels/name/{channel_name}")
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
                  logger.debug(f"User {user_id} likely already in channel {channel_id} (400 returned)")
                  return {}
             raise

    def remove_user_from_channel(self, channel_id: str, user_id: str) -> Dict:
        try:
            return self._request("DELETE", f"/channels/{channel_id}/members/{user_id}")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404: # User not in channel
                return {}
            raise

