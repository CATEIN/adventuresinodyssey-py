"""
Adventures in Odyssey API Authentication Client (Async)
"""

import logging
import json
import base64
import hashlib
import secrets
from pathlib import Path
from collections import Counter
from typing import Optional, Dict, Any, List, Union
from urllib.parse import urlencode, urlparse, parse_qs
import asyncio
import httpx
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from .asyncaioclient import AsyncAIOClient

# Configure logging
logging.basicConfig(
    level=logging.CRITICAL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define the common API prefix to be used for the new generalized methods
API_PREFIX = 'apexrest/v1/'

DEFAULT_FIELDS = {
    "Content__c": ["Name", "Thumbnail_Small__c", "Subtype__c", "Episode_Number__c"],
    "Content_Grouping__c": ["Name", "Image_URL__c", "Type__c"],
    "Topic__c": ["Name"],
    "Author__c": ["Name", "Profile_Image_URL__c"],
    "Character__c": ["Name", "Thumbnail_Small__c"],
    "Badge__c": ["Name", "Icon__c", "Type__c"]
}


class AsyncClubClient(AsyncAIOClient):
    """
    Async authentication client for Adventures in Odyssey API.
    Handles login, token management, and authenticated API requests.
    """

    def __init__(self, email: str, password: str, viewer_id: Optional[str] = None, profile_username: Optional[str] = None, pin: Optional[str] = None, auto_relogin: bool = True, config_path: str = 'club_session.json', timeout: int = 10, browser_executable: Optional[str] = None, browser_args: Optional[List[str]] = None):
        """
        Initialize the AIO API client

        Args:
            email: User's account email address (used for web login).
            password: User's password.
            viewer_id: Optional. The specific Viewer ID (profile) to use. If provided, profile_username is ignored.
            profile_username: Optional. The username of the profile to select after account login. Required if viewer_id is not set.
            pin: Optional. The PIN for the selected profile. Defaults to '0000' if not provided.
        """
        if not email or not password:
            raise ValueError("email and password are required and cannot be empty.")

        super().__init__()
        self.timeout = timeout
        self.browser_executable = browser_executable
        self.browser_args = browser_args if browser_args is not None else []

        # User credentials
        self.email = email
        self.password = password

        # Identity parameters
        self.viewer_id = viewer_id
        self.profile_username = profile_username
        self.pin = pin if pin is not None else "0000"

        # Session tokens
        self._refresh_token: Optional[str] = None
        self.session_token: Optional[str] = None

        # State tracking
        self._login_lock = asyncio.Lock()
        self.logging_in = False
        self.state = "loading"

        # Client configuration
        self.config = {
            'api_base': 'https://fotf.my.site.com/aio/services/',
            'redirect_url': 'https://app.adventuresinodyssey.com/callback',
            'oauth_url': 'https://signin.auth.focusonthefamily.com',
            'api_version': 'v1',
            'client_id': '3MVG9l2zHsylwlpTFc1ZB3ryOQlpLYIqNo0UV4d0lBRjkbb6TXbw9UNhdcJfom2nnbB.AbNpkRbGoTfruF0gB',
            'client_secret': 'B25FC7FE3E4C155E77C73EA2AC72D410E0762C897798816FC257F0C8FA3618AD',
            'auto_relogin': auto_relogin
        }

        self.config_file = Path(config_path)

        self._load_session_state()

        # Default headers for all requests
        self._default_headers = {
            'x-experience-name': 'Adventures In Odyssey',
            'x-viewer-id': self.viewer_id if self.viewer_id else '',
            'x-pin': self.pin
        }

        # httpx async client (initialized lazily or via context manager)
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        """Returns the shared httpx.AsyncClient, creating it if needed."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers=self._default_headers,
                timeout=self.timeout
            )
        return self._client

    async def aclose(self):
        """Close the underlying httpx client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.aclose()

    async def login(self) -> bool:
        """
        Login using Playwright to automate the OAuth flow and select the correct profile.

        Returns:
            bool: True if login successful and profile selected, False otherwise
        """
        async with self._login_lock:
            if self.session_token and await self.check_session():
                logger.info("Login skipped: session already valid.")
                return True

            self.logging_in = True
            self.state = "logging in"
            logger.info("Starting OAuth login...")

            try:
                # --- PHASE 1: OAuth Web Login (Get Session Token) ---

                code_verifier = secrets.token_urlsafe(64)  # 86-char URL-safe random string
                code_challenge = base64.urlsafe_b64encode(
                    hashlib.sha256(code_verifier.encode()).digest()
                ).rstrip(b'=').decode()

                auth_params = {
                    'response_type': 'code',
                    'client_id': self.config['client_id'],
                    'redirect_uri': self.config['redirect_url'],
                    'code_challenge': code_challenge,          # now derived, not hardcoded
                    'code_challenge_method': 'S256',           # tell the server which method
                    'scope': 'api web refresh_token'
                }
                login_url = f"{self.config['api_base']}oauth2/authorize?{urlencode(auth_params)}"

                async with async_playwright() as p:
                    launch_kwargs: Dict[str, Any] = {'headless': True}
                    if self.browser_executable:
                        launch_kwargs['executable_path'] = self.browser_executable
                    if self.browser_args:
                        launch_kwargs['args'] = self.browser_args
                    browser = await p.chromium.launch(**launch_kwargs)
                    page = await browser.new_page()

                    async def block_heavy_resources(route):
                        if route.request.resource_type in ["image", "font"]:
                            await route.abort()
                        else:
                            await route.continue_()

                    await page.route("**/*", block_heavy_resources)

                    logger.info("Navigating to login page...")
                    await page.goto(login_url)

                    # Fill login form
                    await page.get_by_role("textbox", name="Email Address").wait_for(timeout=10000)
                    await page.get_by_role("textbox", name="Email Address").fill(self.email)
                    await page.get_by_role("textbox", name="Password").fill(self.password)

                    # Submit form and wait for navigation/redirect
                    logger.info("Submitting login form and waiting for redirect...")
                    async with page.expect_navigation():
                        await page.click('button[type="submit"]')

                    # Wait for the final redirect to the callback URL
                    await page.wait_for_url(
                        lambda url: url.startswith(self.config['redirect_url']),
                        timeout=30000
                    )
                    callback_url = page.url
                    await browser.close()

                # Exchange authorization code for tokens
                parsed_url = urlparse(callback_url)
                auth_code = parse_qs(parsed_url.query).get('code', [None])[0]

                if not auth_code:
                    raise ValueError("No authorization code ('code' parameter) in callback URL.")

                token_response = await self._exchange_code_for_token(auth_code, code_verifier)

                # Store tokens and update default headers
                self._refresh_token = token_response.get('refresh_token')
                self.session_token = token_response.get('access_token')
                self._update_auth_header()

                logger.info("Account login successful.")

                # --- PHASE 2: Profile Selection (Get Viewer ID) ---
                if not await self._select_profile_and_set_headers():
                    self.state = "profile selection failed"
                    self.session_token = None
                    self._refresh_token = None
                    self.logging_in = False
                    return False

                self.logging_in = False
                self.state = "ready"
                logger.info("Login and profile selection successful!")
                self._save_session_state()

                return True

            except PlaywrightTimeout as e:
                self.state = "login failed"
                self.session_token = None
                self._refresh_token = None
                self.logging_in = False
                logger.error(f"Login failed (Playwright Timeout): {e}")
                raise RuntimeError(f"Failed to login: Playwright timed out. Check credentials or network.")

            except Exception as e:
                self.state = "login failed"
                self.session_token = None
                self._refresh_token = None
                self.logging_in = False
                logger.error(f"Login failed: {e}")
                raise RuntimeError(f"Failed to login: {e}")

    def _update_auth_header(self):
        """Update the Authorization header on the shared client."""
        client = self._get_client()
        client.headers['Authorization'] = f"Bearer {self.session_token}"

    def _save_session_state(self):
        """Saves the essential session data to a local JSON file."""
        if not self._refresh_token or not self.viewer_id:
            logger.debug("Skipping save: Missing refresh token or viewer ID.")
            return

        state = {
            'refresh_token': self._refresh_token,
            'viewer_id': self.viewer_id,
            'pin': self.pin
        }

        try:
            with self.config_file.open('w', encoding='utf-8') as f:
                json.dump(state, f, indent=4)
            logger.info(f"Session state saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save session state: {e}")

    def _load_session_state(self) -> bool:
        """Loads the essential session data from a local JSON file."""
        if not self.config_file.exists():
            return False

        try:
            with self.config_file.open('r', encoding='utf-8') as f:
                state = json.load(f)

            self._refresh_token = state.get('refresh_token')

            if self.viewer_id is None:
                self.viewer_id = state.get('viewer_id')

            if self.pin == "0000" and state.get('pin'):
                self.pin = state.get('pin')

            if self._refresh_token:
                self.state = "ready"
                logger.info("Loaded saved session state. Refresh required.")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to load session state: {e}")
            return False

    async def _fetch_viewer_profiles(self) -> List[Dict[str, Any]]:
        """GET /v1/viewer to retrieve all profiles associated with the account."""
        viewer_url = f"{self.config['api_base']}apexrest/{self.config['api_version']}/viewer"

        try:
            response = await self._get_client().get(viewer_url)
            response.raise_for_status()
            data = response.json()

            profiles = data.get("profiles", [])
            if not profiles:
                logger.warning("Viewer endpoint returned no profiles.")
                return []
            return profiles

        except Exception as e:
            logger.error(f"Failed to fetch viewer profiles: {e}")
            return []

    async def _select_profile_and_set_headers(self) -> bool:
        """
        Determines the Viewer ID, validates PIN if necessary, and sets the final
        x-viewer-id and x-pin headers for subsequent API calls.

        Returns:
            bool: True if profile selection succeeded, False otherwise.
        """
        client = self._get_client()

        # Case 1: Viewer ID was provided directly (highest priority)
        if self.viewer_id:
            logger.info(f"Using provided Viewer ID: {self.viewer_id}")
            client.headers['x-viewer-id'] = self.viewer_id
            client.headers['x-pin'] = self.pin
            return True

        # Need profiles for Case 2 and 3
        profiles = await self._fetch_viewer_profiles()
        if not profiles:
            logger.error("Profile selection failed: Could not retrieve profile list.")
            return False

        selected_profile = None

        # Case 2: Profile username was provided
        if self.profile_username:
            logger.info(f"Searching for profile with username: '{self.profile_username}'")
            selected_profile = next(
                (p for p in profiles if p.get('username') == self.profile_username),
                None
            )

            if not selected_profile:
                logger.error(f"Profile selection failed: Could not find profile with username '{self.profile_username}'.")
                return False

            has_pin = selected_profile.get('hasPIN', False)
            if has_pin and self.pin == "0000":
                logger.error(f"Profile '{self.profile_username}' requires a PIN, but the default PIN '{self.pin}' was used. Login aborted.")
                return False

        # Case 3: Automatic Selection
        elif not self.viewer_id and not self.profile_username:
            logger.info("No Viewer ID or Username provided. Attempting to auto-select first profile with no PIN.")

            selected_profile = next(
                (p for p in profiles if not p.get('hasPIN', False)),
                None
            )

            if not selected_profile:
                logger.error("Auto-selection failed: No profile found that does not require a PIN.")
                return False

            self.pin = "0000"

        if not selected_profile:
            logger.error("Profile selection failed: Could not identify a profile to use.")
            return False

        # --- Final Header Setup ---
        self.viewer_id = selected_profile['viewer_id']
        client.headers['x-viewer-id'] = self.viewer_id
        client.headers['x-pin'] = self.pin

        log_name = selected_profile.get('username', 'N/A')
        logger.info(f"Profile selected: '{log_name}' (Viewer ID: {self.viewer_id}).")

        return True

    async def _exchange_code_for_token(self, auth_code: str, code_verifier: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens."""
        token_url = f"{self.config['api_base']}oauth2/token"
        token_params = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': self.config['redirect_url'],
            'client_id': self.config['client_id'],
            'client_secret': self.config['client_secret'],
            'code_verifier': code_verifier,
        }

        response = await self._get_client().post(token_url, params=token_params)
        response.raise_for_status()

        return response.json()

    async def refresh_session(self) -> bool:
        """Refresh the session using the refresh token."""
        async with self._login_lock:
            if not self._refresh_token:
                logger.info("Session refresh skipped: no refresh token available")
                return False

            try:
                token_url = f"{self.config['api_base']}oauth2/token"
                token_params = {
                    'grant_type': 'refresh_token',
                    'refresh_token': self._refresh_token,
                    'client_id': self.config['client_id'],
                    'client_secret': self.config['client_secret'],
                }

                response = await self._get_client().post(token_url, params=token_params)

                if response.status_code == 200:
                    token_data = response.json()
                    self.session_token = token_data.get('access_token')
                    if token_data.get('refresh_token'):
                        self._refresh_token = token_data.get('refresh_token')

                    self._update_auth_header()
                    logger.info("Token refresh successful!")
                    return True
                else:
                    logger.warning(f"Token refresh failed with status {response.status_code}. Full login will be required.")
                    self.session_token = None
                    self._refresh_token = None
                    return False

            except Exception as e:
                logger.error(f"Session refresh failed: {e}")
                self.session_token = None
                self._refresh_token = None
                return False

    async def check_session(self) -> bool:
        """Check if the current session token is valid and required headers are set."""
        if not self.session_token:
            return False

        client = self._get_client()
        if not client.headers.get('x-viewer-id'):
            logger.debug("Session check failed: x-viewer-id is missing.")
            return False

        try:
            introspect_url = f"{self.config['api_base']}oauth2/introspect"
            introspect_params = {
                'token': self.session_token,
                'token_type_hint': 'access_token',
                'client_id': self.config['client_id'],
                'client_secret': self.config['client_secret']
            }

            response = await client.post(introspect_url, params=introspect_params)

            if response.status_code == 200:
                data = response.json()
                return data.get('active', False)

            return False

        except Exception as e:
            logger.error(f"Session check failed: {e}")
            return False

    async def ensure_authenticated(self) -> bool:
        """
        Ensure the client is authenticated, attempting login/refresh as needed.

        Returns:
            bool: True if authenticated, False otherwise
        """
        if await self.check_session():
            logger.debug("Session is valid.")
            return True

        logger.info("Session invalid, attempting refresh...")
        if await self.refresh_session():
            return True

        if self.config['auto_relogin']:
            logger.info("Refresh failed, attempting full login...")
            return await self.login()
        else:
            logger.warning("Refresh failed. Automatic full login is disabled.")
            return False

    async def change_profile(self, viewer_id: str, pin: str) -> bool:
        """
        Switches the active profile (viewer) for authenticated requests without
        requiring a full web login, as long as the session token is still valid.

        Args:
            viewer_id: The ID of the profile to switch to.
            pin: The PIN associated with the new profile.

        Returns:
            bool: True if the profile was successfully switched and headers updated.
        """
        if self.state != "authenticated":
            logger.warning("Attempted to change profile on an unauthenticated client. Please login first.")
            return False

        logger.info(f"Switching active profile to ID: {viewer_id}...")

        self.viewer_id = viewer_id
        self.pin = pin
        client = self._get_client()
        client.headers['x-viewer-id'] = self.viewer_id
        client.headers['x-pin'] = self.pin

        logger.info("Profile successfully switched. Headers updated.")
        return True

    async def fetch_content(self, content_id: str, page_type: str = 'full') -> Dict[str, Any]:
        """
        Fetches detailed content data for a given ID, based on page_type.

        Args:
            content_id: The ID of the content to fetch (e.g., 'a354W0000046U6OQAU').
            page_type: The type of content page: 'full' (default), 'radio', or 'promo'.

        Returns:
            Dict[str, Any]: The parsed JSON response from the API.

        Raises:
            httpx.HTTPStatusError: If the API request fails after all retry attempts.
        """
        is_radio = (page_type == 'radio')
        is_promo = (page_type == 'promo')

        endpoint = f"content/{content_id}"

        params = {
            'tag': 'true',
            'series': 'true',
            'recommendations': 'true',
            'player': 'true',
            'parent': 'true'
        }

        if is_radio:
            params['radio_page_type'] = 'aired'
            logger.info("Fetching content for 'radio' page type, adding radio_page_type=aired.")

        if not is_promo:
            # Authenticated path — self.get() handles ensure_authenticated + 401 retry
            logger.info(f"Attempting to fetch content ID: {content_id} (Page Type: {page_type})")
            return await self.get(endpoint, params=params)

        # Promo: intentionally unauthenticated, temporary clean client
        logger.info("Fetching content for 'promo' page type (unauthenticated request).")
        url = f"{self.config['api_base']}apexrest/{self.config['api_version']}/{endpoint}"

        async with httpx.AsyncClient(
            headers={'x-experience-name': 'Adventures In Odyssey'},
            timeout=self.timeout
        ) as promo_client:
            try:
                response = await promo_client.get(url, params=params)
                response.raise_for_status()
                logger.info(f"Content fetch successful for ID: {content_id} (Page Type: promo)")
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to fetch content ID {content_id} (Page Type: promo): {e}")
                raise

    async def fetch_badge(self, badge_id: str) -> Dict[str, Any]:
        """
        Fetches detailed data for a badge (sometimes called an adventure).

        Args:
            badge_id: The ID of the badge to fetch (e.g., 'a2pUh0000008GXSIA2').

        Returns:
            Dict[str, Any]: The parsed JSON response from the API.

        Raises:
            httpx.HTTPStatusError: If the API request fails after all retry attempts.
        """
        return await self.get(f"badge/{badge_id}")

    async def send_progress(self, content_id: str, progress: Optional[int] = None, status: str = "") -> Dict[str, Any]:
        """
        Sends playback progress and status updates for a specific content ID.

        Args:
            content_id: The ID of the content being updated.
            progress: The current playback position in seconds (optional).
            status: The playback status, typically 'In Progress' or 'Completed'.

        Returns:
            Dict[str, Any]: The parsed JSON response from the API.

        Raises:
            httpx.HTTPStatusError: If the API request fails after all retry attempts.
        """
        request_payload = {
            "content_id": content_id,
            "status": status,
        }

        if progress is not None:
            request_payload["current_progress"] = progress

        log_info = f"ID: {content_id}, Status: {status}"
        if progress is not None:
            log_info += f", Progress: {progress}s"

        logger.info(f"Attempting to send progress update: ({log_info})")

        return await self.put("content", request_payload)

    async def fetch_random(self) -> Dict[str, Any]:
        """
        Fetches a random piece of content (episode/media) from the API.

        Returns:
            Dict[str, Any]: The parsed JSON response from the API.

        Raises:
            httpx.HTTPStatusError: If the API request fails after all retry attempts.
        """
        return await self.get("content/random")

    async def fetch_badges(self, page_number: int = 1, page_size: int = 25) -> Dict[str, Any]:
        """
        Fetches a paginated list of available badges for the profile.

        Args:
            page_number: The 1-based index of the page to retrieve. Defaults to 1.
            page_size: The number of results per page. Defaults to 25.

        Returns:
            Dict[str, Any]: The parsed JSON response from the API.

        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        request_payload = {
            "type": "Badge",
            "pageNumber": page_number,
            "pageSize": page_size
        }

        log_info = f"Page {page_number}, Size {page_size}"
        logger.info(f"Attempting to fetch badges ({log_info})")

        return await self.post("badge/search", request_payload)

    async def fetch_comments(self, related_id: str = None, page_number: int = 1, page_size: int = 10, order_by: str = "CreatedDate DESC") -> Dict[str, Any]:
        """
        Fetches a paginated list of comments.

        Args:
            related_id: The ID of the content item the comments belong to.
            page_number: The page number to retrieve. Defaults to 1.
            page_size: The number of results per page. Defaults to 10.

        Returns:
            Dict[str, Any]: The parsed JSON response containing the comments.

        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        json_data = {
            "pageNumber": page_number,
            "pageSize": page_size,
            "orderBy": order_by
        }

        if related_id is not None:
            json_data["relatedToId"] = related_id

        return await self.post("comment/search", payload=json_data)

    async def fetch_comment(self, comment_id: str, related_id: str = None) -> Dict[str, Any]:
        """
        Fetches a specific comment by its ID.

        Args:
            comment_id (str): The unique ID of the comment to retrieve.
            related_id (str, optional): The ID of the content item (episode/grouping).

        Returns:
            Dict[str, Any]: The parsed JSON response containing the comment details.
        """
        logger.info(f"Fetching details for comment ID: {comment_id}")

        payload = {"id": comment_id}

        if related_id:
            payload["relatedToId"] = related_id

        return await self.post("comment/search", payload=payload)

    async def find_comment_pages(self) -> List[Dict[str, Any]]:
        """
        Fetches the latest comments, traces replies back to their root content page,
        and returns a list of unique related page IDs, types, and names,
        sorted by the frequency of their appearance (most commented pages first).
        """
        logger.info("Starting process to find unique comment pages (including replies).")

        try:
            response: Dict[str, Any] = await self.fetch_comments(page_size=100)
        except Exception as e:
            logger.error(f"Failed to fetch comments during page lookup: {e}")
            return []

        comments = response.get("comments", [])

        if not comments:
            logger.warning("No comments found in the API response.")
            return []

        logger.debug(f"Successfully retrieved {len(comments)} comments.")

        comment_index: Dict[str, Dict[str, Any]] = {
            comment['id']: comment for comment in comments if 'id' in comment
        }

        def get_ultimate_page_info(
            current_comment: Dict[str, Any]
        ) -> Optional[tuple[str, str, str]]:
            comment_obj = current_comment
            max_depth = 5
            for _ in range(max_depth):
                related_object = comment_obj.get("relatedToObject")

                if related_object and related_object != "Comment":
                    page_id = comment_obj.get("relatedToId")
                    page_name = comment_obj.get("relatedToName")
                    if page_id and page_name:
                        return (page_id, related_object, page_name)
                    else:
                        return None

                elif related_object == "Comment":
                    parent_id = comment_obj.get("inReplyToCommentId")
                    if not parent_id:
                        return None
                    parent_comment = comment_index.get(parent_id)
                    if parent_comment:
                        comment_obj = parent_comment
                        continue
                    else:
                        return None

                return None

            return None

        page_counts = Counter()
        page_details_map: Dict[str, tuple[str, str]] = {}

        for comment in comments:
            page_info = get_ultimate_page_info(comment)
            if page_info:
                page_id, page_type, page_name = page_info
                page_counts[page_id] += 1
                if page_id not in page_details_map:
                    page_details_map[page_id] = (page_type, page_name)

        sorted_page_ids = sorted(page_counts.items(), key=lambda item: item[1], reverse=True)

        result: List[Dict[str, Any]] = []
        for page_id, count in sorted_page_ids:
            page_type, page_name = page_details_map.get(page_id, ("Unknown Type", "Unknown Name"))
            result.append({
                "id": page_id,
                "name": page_name,
                "page_type": page_type,
                "comment_count": count
            })

        logger.info(f"Found {len(result)} unique pages with comments (total comments counted: {sum(page_counts.values())}).")
        return result

    async def post_comment(self, message: str, related_id: str) -> Dict[str, Any]:
        """
        Posts a new comment to a content item (episode, grouping, etc.).

        Args:
            message: The comment text.
            related_id: The ID of the content item the comment is related to.

        Returns:
            Dict[str, Any]: The parsed JSON response.

        Raises:
            ValueError: If the required viewer ID (profile ID) is not set on the client.
        """
        if not hasattr(self, 'viewer_id') or not self.viewer_id:
            raise ValueError("Cannot post comment: viewer_id (profile ID) is not set. Ensure the client is authenticated and a profile is selected.")

        comment_payload = {
            "comment": {
                "relatedToId": related_id,
                "viewerProfileId": self.viewer_id,
                "message": message
            }
        }
        return await self.post("comment", payload=comment_payload)

    async def post_reply(self, message: str, related_id: str) -> Dict[str, Any]:
        """
        Posts a reply to a comment.

        Args:
            message: The reply text.
            related_id: The ID of the comment to reply to.

        Returns:
            Dict[str, Any]: The parsed JSON response.

        Raises:
            ValueError: If the required viewer ID (profile ID) is not set.
        """
        if not hasattr(self, 'viewer_id') or not self.viewer_id:
            raise ValueError("Cannot post comment: viewer_id (profile ID) is not set. Ensure the client is authenticated and a profile is selected.")

        reply_payload = {
            "comment": {
                "relatedToId": related_id,
                "viewerProfileId": self.viewer_id,
                "message": message
            }
        }
        return await self.post("comment", payload=reply_payload)

    async def fetch_bookmarks(self) -> Dict[str, Any]:
        """
        Retrieves all content bookmarked by the current club member.

        Returns:
            Dict[str, Any]: The search results containing bookmarked content.
        """
        endpoint = (
            "content/search?community=Adventures+In+Odyssey"
            "&is_bookmarked=true"
            "&tag=true"
        )
        return await self.get(endpoint)

    async def bookmark(self, content_id: str) -> Dict[str, Any]:
        """
        Creates a new bookmark for a given piece of content.

        Args:
            content_id: The ID of the content item to bookmark.

        Returns:
            Dict[str, Any]: The API response, typically confirming creation.

        Raises:
            ValueError: If the required viewer ID (profile ID) is not set on the client.
        """
        if not self.viewer_id:
            raise ValueError("Cannot create bookmark: viewer_id (profile ID) is not set. Ensure the client is authenticated and a profile is selected.")

        payload = {
            "subject_id": content_id,
            "bookmark_type": "Bookmark",
            "subject_type": "Content__c"
        }
        return await self.post("bookmark", payload=payload)

    async def fetch_profiles(self) -> Dict[str, Any]:
        """
        Fetches the profiles.

        Returns:
            Dict[str, Any]: The parsed JSON response from the API.

        Raises:
            httpx.HTTPStatusError: If the API request fails after all retry attempts.
        """
        return await self.get("viewer")

    async def create_playlist(
        self,
        name: str = "New Playlist",
        image_url: str = "",
        content_ids: List[str] = None,
        playlist_json: Dict[str, Any] = None
    ) -> str:
        """
        Creates a new content grouping (playlist).

        Args:
            name (str): The name of the playlist. Defaults to "New Playlist".
            image_url (str): The URL for the playlist cover image.
            content_ids (List[str]): A list of content/episode IDs.
            playlist_json (Dict[str, Any]): Optional. A complete JSON payload.
                                            If provided, other arguments are ignored.

        Returns:
            str: The ID of the newly created playlist.
        """
        if playlist_json:
            logger.info("Creating playlist using provided custom JSON payload.")
            json_payload = playlist_json
        else:
            if content_ids is None:
                content_ids = []

            content_list_payload = [{"id": cid} for cid in content_ids]
            json_payload = {
                "contentGroupings": [
                    {
                        "name": name,
                        "imageURL": image_url,
                        "contentList": content_list_payload
                    }
                ]
            }
            logger.info(f"Building payload for playlist '{name}' with {len(content_ids)} items.")

        return await self.post("contentgrouping", payload=json_payload)

    async def update_playlist(
        self,
        playlist: Dict[str, Any],
        name: str = None,
        image_url: str = None,
        add_ids: Union[str, List[str]] = None,
        content_ids: List[str] = None,
        remove_ids: Union[str, List[str]] = None
    ) -> Dict[str, Any]:
        """
        Updates an existing playlist by modifying the provided playlist object
        and sending a PUT request.

        Args:
            playlist (dict): The full playlist JSON dictionary.
            name (str): If provided, updates the playlist name.
            image_url (str): If provided, updates the imageURL.
            add_ids (str|list): ID(s) to add to the existing list.
            content_ids (list): If provided, completely replaces the contentList.
            remove_ids (str|list): ID(s) to remove from the existing list.

        Returns:
            Dict[str, Any]: The API response from the PUT request.
        """
        try:
            grouping = playlist['contentGroupings'][0]
            playlist_id = grouping['id']
        except (KeyError, IndexError):
            raise ValueError("Invalid playlist JSON: Could not find 'contentGroupings[0].id'")

        logger.info(f"Preparing update for playlist ID: {playlist_id}")

        if name:
            grouping['name'] = name
        if image_url is not None:
            grouping['imageURL'] = image_url

        def format_id(cid): return {"id": cid}

        if content_ids is not None:
            grouping['contentList'] = [format_id(cid) for cid in content_ids]
        else:
            current_list = grouping.get('contentList', [])
            current_ids = [item['id'] for item in current_list]

            if remove_ids:
                if isinstance(remove_ids, str):
                    remove_ids = [remove_ids]
                current_ids = [cid for cid in current_ids if cid not in remove_ids]

            if add_ids:
                if isinstance(add_ids, str):
                    add_ids = [add_ids]
                for aid in add_ids:
                    if aid not in current_ids:
                        current_ids.append(aid)

            grouping['contentList'] = [format_id(cid) for cid in current_ids]

        endpoint = f"contentgrouping/{playlist_id}"
        logger.info(f"Sending PUT request to {endpoint}")
        return await self.put(endpoint, payload=playlist)

    async def fetch_playlists(self, page_number: int = 1, page_size: int = 25) -> Dict[str, Any]:
        """
        Fetches the custom playlists made by current user.

        Args:
            page_number: The 1-based index of the page to retrieve. Defaults to 1.
            page_size: The number of results per page. Defaults to 25.

        Returns:
            Dict[str, Any]: The parsed JSON response from the API.

        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        request_payload = {
            "type": "Playlist",
            "community": "Adventures in Odyssey",
            "pageNumber": page_number,
            "pageSize": page_size,
            "viewer_id": self.viewer_id,
        }
        return await self.post("contentgrouping/search", request_payload)

    async def fetch_signed_cookie(self, content_type: str = 'audio') -> str:
        """
        Fetches the content data for a known audio or video test ID, extracts the
        signed cookie URL, and returns the query string portion prefixed with '?'.

        Args:
            content_type: The type of content to fetch: 'audio' or 'video'.

        Returns:
            str: The signed cookie URL query string, including the leading '?'.

        Raises:
            ValueError: If an invalid content_type is provided or the cookie URL is missing.
            httpx.HTTPStatusError: If the underlying API request fails.
        """
        if content_type.lower() == 'audio':
            content_id = "a354W0000046V5fQAE"
            logger.info("Fetching signed cookie for known audio content ID.")
        elif content_type.lower() == 'video':
            content_id = "a354W0000046SHtQAM"
            logger.info("Fetching signed cookie for known video content ID.")
        else:
            raise ValueError(f"Invalid content_type '{content_type}'. Must be 'audio' or 'video'.")

        content_data = await self.fetch_content(content_id)

        signed_cookie_url = content_data.get('signed_cookie')

        if not signed_cookie_url:
            logger.error("Signed cookie URL not found in API response.")
            raise ValueError("API response for content ID contains no 'signed_cookie' or similar URL.")

        parsed_url = urlparse(signed_cookie_url)

        if not parsed_url.query:
            logger.error(f"URL contains no query parameters: {signed_cookie_url}")
            raise ValueError("The retrieved signed cookie URL did not contain a query string.")

        logger.info(f"Successfully extracted signed cookie query for ID: {content_id}")
        return '?' + parsed_url.query

    async def delete_comment(self, comment_id: str) -> Dict[str, Any]:
        """
        Deletes an existing comment by its ID.

        Args:
            comment_id (str): The unique ID of the comment to be deleted.

        Returns:
            Dict[str, Any]: The parsed JSON response (often a success status).

        Raises:
            ValueError: If the required viewer ID (profile ID) is not set.
        """
        if not hasattr(self, 'viewer_id') or not self.viewer_id:
            raise ValueError(
                "Cannot delete comment: viewer_id is not set. "
                "Ensure the client is authenticated."
            )

        logger.info(f"Attempting to delete comment with ID: {comment_id}")
        return await self.delete(f"comment/{comment_id}")

    async def delete_playlist(self, playlist_id: str) -> Dict[str, Any]:
        """
        Deletes a specific playlist (content grouping) by its ID.

        Args:
            playlist_id (str): The unique ID of the playlist to be deleted.

        Returns:
            Dict[str, Any]: The parsed JSON response from the server.

        Raises:
            ValueError: If the viewer_id is not set, indicating the client is unauthenticated.
        """
        if not hasattr(self, 'viewer_id') or not self.viewer_id:
            raise ValueError(
                "Cannot delete playlist: viewer_id is not set. "
                "Ensure the client is authenticated and a profile is selected."
            )

        logger.info(f"Attempting to delete playlist with ID: {playlist_id}")
        return await self.delete(f"contentgrouping/{playlist_id}")

    # -------------------------------------------------------------------------
    # Core HTTP methods (async, httpx-based)
    # -------------------------------------------------------------------------

    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Performs an authenticated GET request to a generalized API endpoint.

        Args:
            endpoint: The relative API path (e.g., 'content/random').
            params: Optional dictionary of query parameters.
            headers: Optional dictionary of headers to override or add for this request.

        Returns:
            Dict[str, Any]: The parsed JSON response from the API.

        Raises:
            httpx.HTTPStatusError: If the API request fails after all retry attempts.
        """
        request_timeout = timeout if timeout is not None else self.timeout

        if not await self.ensure_authenticated():
            raise RuntimeError(f"Cannot perform GET request to {endpoint}: Failed to authenticate user.")

        full_endpoint = f"{API_PREFIX}{endpoint}"
        url = f"{self.config['api_base']}{full_endpoint}"

        client = self._get_client()
        request_headers = dict(client.headers)
        if headers:
            request_headers.update(headers)

        async def make_request():
            return await client.get(url, params=params, headers=request_headers, timeout=request_timeout)

        try:
            logger.info(f"Attempting GET request to: {full_endpoint}")
            response = await make_request()

            if response.status_code == 401:
                logger.warning("GET request failed with 401 Unauthorized. Attempting re-authentication...")
                if await self.ensure_authenticated():
                    logger.info("Re-authentication successful. Retrying request...")
                    request_headers = dict(client.headers)
                    if headers:
                        request_headers.update(headers)
                    response = await make_request()
                else:
                    response.raise_for_status()

            response.raise_for_status()
            logger.info(f"GET request successful for: {full_endpoint}")
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"GET request failed for {full_endpoint}: {e}")
            raise

    async def post(self, endpoint: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Performs an authenticated POST request to a generalized API endpoint with JSON data.

        Args:
            endpoint: The relative API path (e.g., 'contentgrouping/search').
            payload: The JSON dictionary to be sent in the request body.
            headers: Optional dictionary of headers to override or add for this request.

        Returns:
            Dict[str, Any]: The parsed JSON response from the API.

        Raises:
            httpx.HTTPStatusError: If the API request fails after all retry attempts.
        """
        request_timeout = timeout if timeout is not None else self.timeout

        if not await self.ensure_authenticated():
            raise RuntimeError(f"Cannot perform POST request to {endpoint}: Failed to authenticate user.")

        full_endpoint = f"{API_PREFIX}{endpoint}"
        url = f"{self.config['api_base']}{full_endpoint}"

        client = self._get_client()
        request_headers = dict(client.headers)
        if headers:
            request_headers.update(headers)

        async def make_request():
            return await client.post(url, json=payload, headers=request_headers, timeout=request_timeout)

        try:
            logger.info(f"Attempting POST request to: {full_endpoint}")
            response = await make_request()

            if response.status_code == 401:
                logger.warning("POST request failed with 401 Unauthorized. Attempting re-authentication...")
                if await self.ensure_authenticated():
                    logger.info("Re-authentication successful. Retrying request...")
                    request_headers = dict(client.headers)
                    if headers:
                        request_headers.update(headers)
                    response = await make_request()
                else:
                    response.raise_for_status()

            response.raise_for_status()
            logger.info(f"POST request successful for: {full_endpoint}")
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"POST request failed for {full_endpoint}: {e}")
            raise

    async def put(self, endpoint: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Performs an authenticated PUT request to a generalized API endpoint with JSON data.

        Args:
            endpoint: The relative API path (e.g., 'content').
            payload: The JSON dictionary to be sent in the request body.
            headers: Optional dictionary of headers to override or add for this request.

        Returns:
            Dict[str, Any]: The parsed JSON response from the API, or a success dictionary if no content is returned.

        Raises:
            httpx.HTTPStatusError: If the API request fails after all retry attempts.
        """
        request_timeout = timeout if timeout is not None else self.timeout

        if not await self.ensure_authenticated():
            raise RuntimeError(f"Cannot perform PUT request to {endpoint}: Failed to authenticate user.")

        full_endpoint = f"{API_PREFIX}{endpoint}"
        url = f"{self.config['api_base']}{full_endpoint}"

        client = self._get_client()
        request_headers = dict(client.headers)
        if headers:
            request_headers.update(headers)

        async def make_request():
            return await client.put(url, json=payload, headers=request_headers, timeout=request_timeout)

        try:
            logger.info(f"Attempting PUT request to: {full_endpoint}")
            response = await make_request()

            if response.status_code == 401:
                logger.warning("PUT request failed with 401 Unauthorized. Attempting re-authentication...")
                if await self.ensure_authenticated():
                    logger.info("Re-authentication successful. Retrying request...")
                    request_headers = dict(client.headers)
                    if headers:
                        request_headers.update(headers)
                    response = await make_request()
                else:
                    response.raise_for_status()

            response.raise_for_status()
            logger.info(f"PUT request successful for: {full_endpoint}")
            return response.json() if response.content else {"status": "success"}

        except httpx.HTTPStatusError as e:
            logger.error(f"PUT request failed for {full_endpoint}: {e}")
            raise

    async def patch(self, endpoint: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Performs an authenticated PATCH request to a generalized API endpoint with JSON data.

        Args:
            endpoint: The relative API path (e.g., 'contentgrouping/search').
            payload: The JSON dictionary to be sent in the request body.
            headers: Optional dictionary of headers to override or add for this request.

        Returns:
            Dict[str, Any]: The parsed JSON response from the API.

        Raises:
            httpx.HTTPStatusError: If the API request fails after all retry attempts.
        """
        request_timeout = timeout if timeout is not None else self.timeout

        if not await self.ensure_authenticated():
            raise RuntimeError(f"Cannot perform PATCH request to {endpoint}: Failed to authenticate user.")

        full_endpoint = f"{API_PREFIX}{endpoint}"
        url = f"{self.config['api_base']}{full_endpoint}"

        client = self._get_client()
        request_headers = dict(client.headers)
        if headers:
            request_headers.update(headers)

        async def make_request():
            return await client.patch(url, json=payload, headers=request_headers, timeout=request_timeout)

        try:
            logger.info(f"Attempting PATCH request to: {full_endpoint}")
            response = await make_request()

            if response.status_code == 401:
                logger.warning("PATCH request failed with 401 Unauthorized. Attempting re-authentication...")
                if await self.ensure_authenticated():
                    logger.info("Re-authentication successful. Retrying request...")
                    request_headers = dict(client.headers)
                    if headers:
                        request_headers.update(headers)
                    response = await make_request()
                else:
                    response.raise_for_status()

            response.raise_for_status()
            logger.info(f"PATCH request successful for: {full_endpoint}")
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"PATCH request failed for {full_endpoint}: {e}")
            raise

    async def delete(self, endpoint: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Performs an authenticated DELETE request to a generalized API endpoint.

        Args:
            endpoint: The relative API path (e.g., 'content/123').
            params: Optional dictionary of query parameters.
            headers: Optional dictionary of headers to override or add for this request.

        Returns:
            Dict[str, Any]: The parsed JSON response from the API.

        Raises:
            httpx.HTTPStatusError: If the API request fails after all retry attempts.
        """
        request_timeout = timeout if timeout is not None else self.timeout

        if not await self.ensure_authenticated():
            raise RuntimeError(f"Cannot perform DELETE request to {endpoint}: Failed to authenticate user.")

        full_endpoint = f"{API_PREFIX}{endpoint}"
        url = f"{self.config['api_base']}{full_endpoint}"

        client = self._get_client()
        request_headers = dict(client.headers)
        if headers:
            request_headers.update(headers)

        async def make_request():
            return await client.delete(url, params=params, headers=request_headers, timeout=request_timeout)

        try:
            logger.info(f"Attempting DELETE request to: {full_endpoint}")
            response = await make_request()

            if response.status_code == 401:
                logger.warning("DELETE request failed with 401 Unauthorized. Attempting re-authentication...")
                if await self.ensure_authenticated():
                    logger.info("Re-authentication successful. Retrying request...")
                    request_headers = dict(client.headers)
                    if headers:
                        request_headers.update(headers)
                    response = await make_request()
                else:
                    response.raise_for_status()

            response.raise_for_status()
            logger.info(f"DELETE request successful for: {full_endpoint}")
            if response.text.strip():
                try:
                    return response.json()
                except Exception:
                    return {"status": "success", "message": response.text}

            return {"status": "success", "code": response.status_code}

        except httpx.HTTPStatusError as e:
            logger.error(f"DELETE request failed for {full_endpoint}: {e}")
            raise