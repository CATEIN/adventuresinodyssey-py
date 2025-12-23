"""
Adventures in Odyssey API Authentication Client
"""

import logging
import json
from pathlib import Path
from collections import Counter
from typing import Optional, Dict, Any, List, Union
from urllib.parse import urlencode, urlparse, parse_qs
import requests
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout
from .aioclient import AIOClient

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


class ClubClient(AIOClient):
    """
    Authentication client for Adventures in Odyssey API. 
    Handles login, token management, and authenticated API requests.
    """
    
    def __init__(self, email: str, password: str, viewer_id: Optional[str] = None, profile_username: Optional[str] = None, pin: Optional[str] = None, auto_relogin: bool = True, config_path: str = 'club_session.json'):
        """
        Initialize the AIO API client
        
        Args:
            email: User's account email address (used for web login).
            password: User's password.
            viewer_id: Optional. The specific Viewer ID (profile) to use. If provided, profile_username is ignored.
            profile_username: Optional. The username of the profile to select after account login. Required if viewer_id is not set.
            pin: Optional. The PIN for the selected profile. Defaults to '0000' if not provided.
        """

        super().__init__()

        # User credentials
        self.email = email
        self.password = password
        
        # Identity parameters
        self.viewer_id = viewer_id # User-provided ID, or None if derived from profile_username
        self.profile_username = profile_username
        self.pin = pin if pin is not None else "0000"
        
        # Session tokens
        self._refresh_token: Optional[str] = None
        self.session_token: Optional[str] = None
        
        # State tracking
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
        
        # Setup HTTP session
        self.session = requests.Session()
        self.session.headers.update({
            'x-experience-name': 'Adventures In Odyssey',
            # These are set temporarily/initially. Will be finalized in _select_profile_and_set_headers
            'x-viewer-id': self.viewer_id if self.viewer_id else '',
            'x-pin': self.pin
        })
    
    def login(self) -> bool:
        """
        Login using Playwright to automate the OAuth flow and select the correct profile.
        
        Returns:
            bool: True if login successful and profile selected, False otherwise
        """
        if self.logging_in:
            logger.info("Login already in progress")
            return False
        
        self.logging_in = True
        self.state = "logging in"
        logger.info("Starting OAuth login...")
        
        try:
            # --- PHASE 1: OAuth Web Login (Get Session Token) ---
            
            auth_params = {
                'response_type': 'code',
                'client_id': self.config['client_id'],
                'redirect_uri': self.config['redirect_url'],
                'scope': 'api web refresh_token'
            }
            login_url = f"{self.config['api_base']}oauth2/authorize?{urlencode(auth_params)}"
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.route("**/*.{png,jpg,jpeg}", lambda route: route.abort())
                
                logger.info("Navigating to login page...")
                page.goto(login_url)
                
                # Fill login form
                # Ensure the selector is correct and fields are visible
                page.get_by_role("textbox", name="Email Address").wait_for(timeout=10000)
                page.get_by_role("textbox", name="Email Address").fill(self.email) # Use self.email now
                page.get_by_role("textbox", name="Password").fill(self.password)
                
                # Submit form and wait for navigation/redirect
                logger.info("Submitting login form and waiting for redirect...")
                with page.expect_navigation():
                    page.click('button[type="submit"]')
                
                # Wait for the final redirect to the callback URL
                page.wait_for_url(
                    lambda url: url.startswith(self.config['redirect_url']),
                    timeout=30000
                )
                callback_url = page.url
                browser.close()
            
            # Exchange authorization code for tokens
            parsed_url = urlparse(callback_url)
            auth_code = parse_qs(parsed_url.query).get('code', [None])[0]
            
            if not auth_code:
                raise ValueError("No authorization code ('code' parameter) in callback URL.")
            
            token_response = self._exchange_code_for_token(auth_code)
            
            # Store tokens and update session header
            self._refresh_token = token_response.get('refresh_token')
            self.session_token = token_response.get('access_token')
            self.session.headers['Authorization'] = f"Bearer {self.session_token}"
            
            logger.info("Account login successful.")
            
            # --- PHASE 2: Profile Selection (Get Viewer ID) ---
            if not self._select_profile_and_set_headers():
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
            # Raise RuntimeError to be caught by calling function
            raise RuntimeError(f"Failed to login: {e}")
        
    def _save_session_state(self):
        """Saves the essential session data to a local JSON file."""
        if not self._refresh_token or not self.viewer_id:
            logger.debug("Skipping save: Missing refresh token or viewer ID.")
            return

        state = {
            'refresh_token': self._refresh_token,
            'viewer_id': self.viewer_id,
            # Note: Storing the PIN is a security risk, but required for profile switching.
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

            # 1. ALWAYS load the refresh token (this is the core of persistence)
            self._refresh_token = state.get('refresh_token')
            
            # 2. CONDITIONALLY load profile parameters
            
            # The viewer_id is only None if the user did NOT pass it to the constructor.
            # If the user supplied a viewer_id, we keep that new value.
            if self.viewer_id is None:
                self.viewer_id = state.get('viewer_id')
                
            # The pin defaults to "0000". If the user did NOT supply a pin 
            # (and it's currently "0000"), and the file has one, load the file's pin.
            # If the user supplied a custom pin (e.g., "1234"), we keep "1234".
            # This assumes the original value of self.pin is only "0000" if no pin was supplied.
            if self.pin == "0000" and state.get('pin'): 
                self.pin = state.get('pin')
            
            # Since the session token is short-lived, we *MUST* immediately try to refresh
            # to get a new access token before any API calls are made.
            # We don't call self.refresh_session() here because it depends on the 
            # self.session object and headers being set up, which happens *after* __init__.
            
            # The presence of the refresh_token is enough to signal that a saved session exists.
            if self._refresh_token:
                # Set state to ready, as we expect a refresh to follow
                self.state = "ready"
                logger.info("Loaded saved session state. Refresh required.")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Failed to load session state: {e}")
            return False
            
    def _fetch_viewer_profiles(self) -> List[Dict[str, Any]]:
        """GET /v1/viewer to retrieve all profiles associated with the account."""
        viewer_url = f"{self.config['api_base']}apexrest/{self.config['api_version']}/viewer"
        
        try:
            # Note: This API call needs the Authorization header set from Phase 1, 
            # but *before* the final x-viewer-id is set.
            response = self.session.get(viewer_url)
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

    def _select_profile_and_set_headers(self) -> bool:
        """
        Determines the Viewer ID, validates PIN if necessary, and sets the final 
        x-viewer-id and x-pin headers for subsequent API calls.
        
        The selection priority is:
        1. Explicit self.viewer_id
        2. Explicit self.profile_username (with PIN check)
        3. Automatic selection of the first profile without a PIN (if neither ID nor username is set)
        
        Returns:
            bool: True if profile selection succeeded, False otherwise.
        """
        # Case 1: Viewer ID was provided directly (highest priority)
        if self.viewer_id:
            logger.info(f"Using provided Viewer ID: {self.viewer_id}")
            self.session.headers['x-viewer-id'] = self.viewer_id
            self.session.headers['x-pin'] = self.pin
            return True

        # Need profiles for Case 2 and 3
        profiles = self._fetch_viewer_profiles()
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
                # Pin is required but user did not provide one (using default "0000")
                logger.error(f"Profile '{self.profile_username}' requires a PIN, but the default PIN '{self.pin}' was used. Login aborted.")
                return False
        
        # Case 3: Automatic Selection (if neither Viewer ID nor Username was provided)
        elif not self.viewer_id and not self.profile_username: 
            logger.info("No Viewer ID or Username provided. Attempting to auto-select first profile with no PIN.")
            
            # Find the first profile that does not have a PIN
            selected_profile = next(
                (p for p in profiles if not p.get('hasPIN', False)),
                None
            )
            
            if not selected_profile:
                logger.error("Auto-selection failed: No profile found that does not require a PIN.")
                return False
            
            # For auto-selection of a no-PIN profile, ensure the pin header is '0000'
            self.pin = "0000"
            
        # If no profile was selected by any case, return False
        if not selected_profile:
            logger.error("Profile selection failed: Could not identify a profile to use.")
            return False

        # --- Final Header Setup ---
        self.viewer_id = selected_profile['viewer_id']
        self.session.headers['x-viewer-id'] = self.viewer_id
        # self.pin is already correctly set by Case 1, 2, or 3
        self.session.headers['x-pin'] = self.pin 
        
        log_name = selected_profile.get('username', 'N/A')
        logger.info(f"Profile selected: '{log_name}' (Viewer ID: {self.viewer_id}).")
        
        return True

    def _exchange_code_for_token(self, auth_code: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens."""
        token_url = f"{self.config['api_base']}oauth2/token"
        token_params = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': self.config['redirect_url'],
            'client_id': self.config['client_id'],
            'client_secret': self.config['client_secret']
        }
        
        response = self.session.post(token_url, params=token_params)
        response.raise_for_status()
        
        return response.json()
    
    def refresh_session(self) -> bool:
        """Refresh the session using the refresh token."""
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
            
            response = self.session.post(token_url, params=token_params)
            
            if response.status_code == 200:
                token_data = response.json()
                self.session_token = token_data.get('access_token')
                if token_data.get('refresh_token'):
                    self._refresh_token = token_data.get('refresh_token')
                
                self.session.headers['Authorization'] = f"Bearer {self.session_token}"
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
    
    def check_session(self) -> bool:
        """Check if the current session token is valid and required headers are set."""
        if not self.session_token:
            return False
        
        # Check if the required headers are set (Viewer ID is essential for API calls)
        if not self.session.headers.get('x-viewer-id'):
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
            
            response = self.session.post(introspect_url, params=introspect_params)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('active', False)
            
            return False
            
        except Exception as e:
            logger.error(f"Session check failed: {e}")
            return False
    
    def ensure_authenticated(self) -> bool:
        """
        Ensure the client is authenticated, attempting login/refresh as needed.
        
        Returns:
            bool: True if authenticated, False otherwise
        """
        # 1. Check if current session is valid
        if self.check_session():
            logger.debug("Session is valid.")
            return True
        
        # 2. Try to refresh session
        logger.info("Session invalid, attempting refresh...")
        if self.refresh_session():
            return True
        
        # 3. Fall back to full login (Only if enabled)
        if self.config['auto_relogin']:
            logger.info("Refresh failed, attempting full login...")
            return self.login()
        else:
            logger.warning("Refresh failed. Automatic full login is disabled.")
            return False # Return False if we can't refresh and can't relogin
    
    def change_profile(self, viewer_id: str, pin: str) -> bool:
        """
        Switches the active profile (viewer) for authenticated requests without
        requiring a full web login, as long as the session token is still valid.
        
        This updates the 'x-viewer-id' and 'x-pin' headers for all subsequent API calls.
        
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
        self.session.headers['x-viewer-id'] = self.viewer_id
        self.session.headers['x-pin'] = self.pin
        
        logger.info("Profile successfully switched. Headers updated.")
        return True

    def fetch_content(self, content_id: str, page_type: str = 'full') -> Dict[str, Any]:
        """
        Fetches detailed content data for a given ID, based on page_type.
        
        Args:
            content_id: The ID of the content to fetch (e.g., 'a354W0000046U6OQAU').
            page_type: The type of content page: 'full' (default), 'radio', or 'promo'.
            
        Returns:
            Dict[str, Any]: The parsed JSON response from the API.
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails after all retry attempts.
        """
        # Determine authentication requirement and request parameters
        needs_auth = (page_type != 'promo')
        is_radio = (page_type == 'radio')
        
        # 1. Handle Authentication if required
        if needs_auth:
            if not self.ensure_authenticated():
                raise RuntimeError(f"Cannot fetch content for page_type '{page_type}': Failed to authenticate user.")
            
            session_to_use = self.session
            
        else:
            # Promo page type requires NO authentication/viewer/pin headers
            logger.info("Fetching content for 'promo' page type (unauthenticated request).")
            
            # Use a clean set of headers, keeping only the experience name if necessary
            headers = {'x-experience-name': 'Adventures In Odyssey'}
            # Temporarily remove default Authorization header for this request type
            session_to_use = requests.Session()
            session_to_use.headers.update(headers)
            
        # Base API URL structure for content details
        endpoint = f"apexrest/{self.config['api_version']}/content/{content_id}"
        url = f"{self.config['api_base']}{endpoint}"

        # Standard default parameters for 'full' and 'promo'
        params = {
            'tag': 'true',
            'series': 'true',
            'recommendations': 'true',
            'player': 'true',
            'parent': 'true'
        }

        if is_radio:
            # Add radio-specific parameter
            params['radio_page_type'] = 'aired'
            logger.info("Fetching content for 'radio' page type, adding radio_page_type=aired.")

        def make_request():
            response = session_to_use.get(url, params=params)
            return response

        try:
            # 1. Initial attempt
            logger.info(f"Attempting to fetch content ID: {content_id} (Page Type: {page_type})")
            response = make_request()

            # 2. Handle Unauthorized (401) ONLY if authentication was required (needs_auth)
            if needs_auth and response.status_code == 401:
                logger.warning("Initial request failed with 401 Unauthorized. Attempting re-authentication...")
                
                # Try to refresh/re-login
                if self.ensure_authenticated():
                    logger.info("Re-authentication successful. Retrying request...")
                    # 3. Retry attempt
                    response = make_request()
                else:
                    # If re-authentication failed, raise the initial 401 error
                    response.raise_for_status() 

            # Raise for any other non-2xx status codes (400, 403, 404, 500 etc.)
            response.raise_for_status()
            
            logger.info(f"Content fetch successful for ID: {content_id} (Page Type: {page_type})")
            return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error(f"Failed to fetch content ID {content_id} (Page Type: {page_type}): {e}")
            raise
        
    def fetch_badge(self, badge_id: str) -> Dict[str, Any]:
        """
        Fetches detailed data for a badge (sometimes called an adventure).
        
        Args:
            badge_id: The ID of the badge to fetch (e.g., 'a2pUh0000008GXSIA2').
            
        Returns:
            Dict[str, Any]: The parsed JSON response from the API.
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails after all retry attempts.
        """
        return self.get(f"badges/{badge_id}")
            
    def send_progress(self, content_id: str, progress: int, status: str) -> Dict[str, Any]:
        """
        Sends playback progress and status updates for a specific content ID.
        
        Sends a PUT request to /v1/content with a JSON body.
        
        Args:
            content_id: The ID of the content being updated.
            progress: The current playback position in seconds (integer).
            status: The playback status, typically 'In Progress' or 'Completed'.
            
        Returns:
            Dict[str, Any]: The parsed JSON response from the API (usually success confirmation).
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails after all retry attempts.
        """
        
        request_payload = {
            "content_id": content_id,
            "status": status,
            "current_progress": progress
        }
        
        log_info = f"ID: {content_id}, Status: {status}, Progress: {progress}s"
        logger.info(f"Attempting to send progress update: ({log_info})")

        return self.put("content", request_payload)


    def fetch_random(self) -> Dict[str, Any]:
        """
        Fetches a random piece of content (episode/media) from the API.
        
        Returns:
            Dict[str, Any]: The parsed JSON response from the API.
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails after all retry attempts.
        """
        return self.get("content/random")

    def fetch_badges(self, page_number: int = 1, page_size: int = 25) -> Dict[str, Any]:
        """
        Fetches a paginated list of available badges for the profile.
        
        Args:
            page_number: The 1-based index of the page to retrieve. Defaults to 1.
            page_size: The number of results per page. Defaults to 25.
            
        Returns:
            Dict[str, Any]: The parsed JSON response from the API.
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails.
        """
        request_payload = {
            "type": "Badge",
            "pageNumber": page_number,
            "pageSize": page_size
        }
        
        log_info = f"Page {page_number}, Size {page_size}"
        logger.info(f"Attempting to fetch badges ({log_info})")
        
        return self.post("badge/search", request_payload)
    
    
    def fetch_comments(self, related_id: str = None, page_number: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """
        Fetches a paginated list of comments. Can fetch comments related to a 
        specific content item or fetch a general list of comments if no ID is provided.
        
        Args:
            related_id: The ID of the content item (e.g., episode, grouping) the comments 
                        belong to. Defaults to None, in which case the API should return 
                        a general list.
            page_number: The page number to retrieve. Defaults to 1.
            page_size: The number of results per page. Defaults to 10.
            
        Returns:
            Dict[str, Any]: The parsed JSON response containing the comments.
        
        Raises:
            requests.exceptions.HTTPError: If the API request fails.
        """
        
        json_data = {
            "pageNumber": page_number,
            "pageSize": page_size,
            "orderBy": "CreatedDate DESC"
        }

        # Only include 'relatedToId' in the payload if a related_id was actually passed.
        if related_id is not None:
            json_data["relatedToId"] = related_id

        # POST to: apexrest/v1/comment/search
        return self.post("comment/search", payload=json_data)
    
    def find_comment_pages(self) -> List[Dict[str, Any]]:
        """
        Fetches the latest comments, traces replies back to their root content page,
        and returns a list of unique related page IDs, types, and names, 
        sorted by the frequency of their appearance (most commented pages first).
        
        All root comments and replies found in the sample are counted toward the page.
        """
        
        logger.info("Starting process to find unique comment pages (including replies).")
        
        try:
            # Fetch comments (using a large page size for better thread coverage)
            response: Dict[str, Any] = self.fetch_comments(page_size=100)
        except Exception as e:
            logger.error(f"Failed to fetch comments during page lookup: {e}")
            return [] 
        
        comments = response.get("comments", [])
        
        if not comments:
            logger.warning("No comments found in the API response.")
            return []
            
        logger.debug(f"Successfully retrieved {len(comments)} comments.")

        # --- STEP 1: Index all comments for efficient tracing ---
        # Map: Comment ID -> Full Comment Object
        comment_index: Dict[str, Dict[str, Any]] = {
            comment['id']: comment for comment in comments if 'id' in comment
        }
        
        # --- STEP 2: Tracing Helper Function ---
        def get_ultimate_page_info(
            current_comment: Dict[str, Any]
        ) -> Optional[tuple[str, str, str]]:
            """
            Recursively traces a comment's parent thread until the ultimate 
            content page is found (relatedToObject != "Comment").
            Returns (page_id, page_type, page_name) or None if the thread 
            root is not in the current sample.
            """
            # Start with the current comment
            comment_obj = current_comment
            
            # Use a safe loop to prevent infinite recursion, though unlikely here
            max_depth = 5 
            for _ in range(max_depth):
                related_object = comment_obj.get("relatedToObject")
                
                # Check if we have hit the root comment (attached to a page)
                if related_object and related_object != "Comment":
                    page_id = comment_obj.get("relatedToId")
                    page_name = comment_obj.get("relatedToName")
                    
                    if page_id and page_name:
                        return (page_id, related_object, page_name)
                    else:
                        # Root found, but details are missing (shouldn't happen)
                        return None 

                # If it is a reply, we must trace back
                elif related_object == "Comment":
                    parent_id = comment_obj.get("inReplyToCommentId")
                    
                    if not parent_id:
                        # Reply has no parent ID, stop tracing
                        return None
                        
                    # Look up the parent in the index
                    parent_comment = comment_index.get(parent_id)
                    
                    if parent_comment:
                        # Found parent in the sample, continue tracing
                        comment_obj = parent_comment
                        continue
                    else:
                        # Parent not found in the sample (outside the 100), stop tracing
                        return None
                
                # Default case for unexpected structure
                return None 
            
            # If max depth is reached
            return None

        # --- STEP 3: Count and Map All Comments (including replies) ---
        page_counts = Counter()
        # Map: Page ID -> (Page Type, Page Name)
        page_details_map: Dict[str, tuple[str, str]] = {} 

        for comment in comments:
            page_info = get_ultimate_page_info(comment)
            
            if page_info:
                page_id, page_type, page_name = page_info
                
                # 1. Count: Increment the count for the ultimate page ID
                page_counts[page_id] += 1
                
                # 2. Map: Store page details (Name and Type)
                if page_id not in page_details_map:
                    page_details_map[page_id] = (page_type, page_name)

        # --- STEP 4: Format the final output ---
        
        # Sort the unique page IDs by count (most frequent first)
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

    def post_comment(self, message: str, related_id: str) -> Dict[str, Any]:
        """
        Posts a new comment to a content item (episode, grouping, etc.).
        
        This requires the client to be fully authenticated with a selected profile.
        
        Args:
            message: The comment text.
            related_id: The ID of the content item the comment is related to.
            
        Returns:
            Dict[str, Any]: The parsed JSON response (often status of the posted comment).
            
        Raises:
            ValueError: If the required viewer ID (profile ID) is not set on the client.
        """
        # Ensure the viewer ID (profile ID) is available from the login process
        if not hasattr(self, 'viewer_id') or not self.viewer_id:
            raise ValueError("Cannot post comment: viewer_id (profile ID) is not set. Ensure the client is authenticated and a profile is selected.")

        comment_payload = {
            "comment": {
                # This ID links the comment to the content item
                "relatedToId": related_id, 
                # This ID identifies the profile posting the comment
                "viewerProfileId": self.viewer_id, 
                "message": message
            }
        }
        # POST to: apexrest/v1/comment
        # ClubClient's post method will handle authentication and retries
        return self.post("comment", payload=comment_payload)
    
    def post_reply(self, message: str, related_id: str) -> Dict[str, Any]:
        """
        Posts a reply to a comment.
        
        This requires the client to be fully authenticated with a selected profile.
        
        Args:
            message: The reply text.
            related_id: The ID of the comment to reply to.
            
        Returns:
            Dict[str, Any]: The parsed JSON response (often status of the posted comment).
            
        Raises:
            ValueError: If the required viewer ID (profile ID) is not set on the client.
        """
        # Ensure the viewer ID (profile ID) is available from the login process
        if not hasattr(self, 'viewer_id') or not self.viewer_id:
            raise ValueError("Cannot post comment: viewer_id (profile ID) is not set. Ensure the client is authenticated and a profile is selected.")

        reply_payload = {
                # This ID links the comment to the content item
                "relatedToId": related_id, 
                # This ID identifies the profile posting the comment
                "viewerProfileId": self.viewer_id, 
                "message": message
        }
        # POST to: apexrest/v1/comment
        # ClubClient's post method will handle authentication and retries
        return self.post("comment", payload=reply_payload)
    
    def fetch_bookmarks(self) -> Dict[str, Any]:
        """
        Retrieves all content bookmarked by the current club member.
        
        Returns:
            Dict[str, Any]: The search results containing bookmarked content.
        """
        # The API endpoint is a GET request with all necessary query parameters
        endpoint = (
            "content/search?community=Adventures+In+Odyssey"
            "&is_bookmarked=true"
            "&tag=true"
        )
        # Use the ClubClient's authenticated GET method
        return self.get(endpoint)

    def bookmark(self, content_id: str) -> Dict[str, Any]:
        """
        Creates a new bookmark for a given piece of content.
        
        Args:
            content_id: The ID of the content item to bookmark (e.g., an episode ID).
            
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
        
        # POST to: apexrest/v1/bookmark
        # Use the ClubClient's authenticated POST method
        return self.post("bookmark", payload=payload)
    
    def fetch_profiles(self) -> Dict[str, Any]:
        """
        Fetches the profiles.
        
        Returns:
            Dict[str, Any]: The parsed JSON response from the API.
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails after all retry attempts.
        """
        return self.get("viewer")
    
    def create_playlist(self, json_payload: dict) -> str:
        """
        Creates a new content grouping (playlist) by directly posting the 
        provided JSON payload to the /v1/contentgrouping endpoint.

        This simplified version bypasses argument construction and requires
        the caller to provide the complete request body.

        Args:
            json_payload: A dictionary representing the full request body 
                        for the API call, e.g., {"contentGroupings": [ ... ]}.

        Returns:
            str: The ID of the newly created playlist (e.g., 'a31Up000007WmVJIA0').

        Raises:
            RuntimeError: If authentication fails.
            requests.exceptions.HTTPError: If the API request fails.
            KeyError: If the API response structure is unexpected.
            ValueError: If the required payload structure is not present.
        """
        
        # --- Validation and Logging ---
        try:
            # Attempt to extract the playlist name for logging purposes
            playlist_name = json_payload['contentGroupings'][0]['name']
            num_items = len(json_payload['contentGroupings'][0]['contentList'])
            log_info = f"Name: {playlist_name}, Items: {num_items}"
        except (KeyError, IndexError):
            # If structure is missing, just use a generic log and raise a clear error
            logger.warning("JSON payload does not conform to expected 'contentGroupings[0]['name']' structure.")
            log_info = "Malformed Payload (details missing)"
            
        if not json_payload.get('contentGroupings'):
            raise ValueError("JSON payload must contain the 'contentGroupings' key.")

        logger.info(f"Attempting to create new playlist with direct JSON payload: ({log_info})")

        # --- API Call ---
        # The base URL and API prefix are handled by self.post
        # POST to: apexrest/v1/contentgrouping
        response = self.post("contentgrouping", payload=json_payload)
        
        # --- Response Parsing ---
        # Expected response structure:
        # { "metadata": {}, "errors": [], "contentGroupings": [ { "id": "...", ... } ] }
        
        try:
            # Extract the ID of the first (and only) grouping in the response list
            playlist_id = response['contentGroupings'][0]['id']
            logger.info(f"Playlist successfully created with ID: {playlist_id}")
            return playlist_id
            
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to parse playlist ID from API response: {e}")
            logger.debug(f"Raw Response: {response}")
            raise KeyError("API response was missing the expected 'contentGroupings[0]['id']' field.")
        
    def fetch_playlists(self, page_number: int = 1, page_size: int = 25) -> Dict[str, Any]:
        """
        Fetches the custom playlists made by current user.
        
        Args:
            page_number: The 1-based index of the page to retrieve. Defaults to 1.
            page_size: The number of results per page. Defaults to 25.
            
        Returns:
            Dict[str, Any]: The parsed JSON response from the API.
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails.
        """
        
        request_payload = {
                "type": "Playlist",
                "community": "Adventures in Odyssey",
                "pageNumber": page_number,
                "pageSize": page_size,
                "viewer_id": self.viewer_id,
            }
        
        # Uses the unauthenticated post helper
        return self.post("contentgrouping/search", request_payload)
        
    def fetch_signed_cookie(self, content_type: str = 'audio') -> str:
        """
        Fetches the content data for a known audio or video test ID, extracts the 
        signed cookie URL, and returns the query string portion *prefixed with '?'*.

        Args:
            content_type: The type of content to fetch: 'audio' or 'video'.

        Returns:
            str: The signed cookie URL query string, including the leading '?' (e.g., ?Policy=...&Signature=...&Key-Pair-Id=...).

        Raises:
            ValueError: If an invalid content_type is provided or the cookie URL is missing.
            requests.exceptions.HTTPError: If the underlying API request fails.
        """
        if content_type.lower() == 'audio':
            content_id = "a354W0000046V5fQAE"
            logger.info("Fetching signed cookie for known audio content ID.")
        elif content_type.lower() == 'video':
            content_id = "a354W0000046SHtQAM"
            logger.info("Fetching signed cookie for known video content ID.")
        else:
            raise ValueError(f"Invalid content_type '{content_type}'. Must be 'audio' or 'video'.")

        # 1. Fetch the content data
        # Note: This uses the default 'full' page_type, which is authenticated.
        content_data = self.fetch_content(content_id)

        # 2. Extract the signed cookie URL
        # The key for the signed content URL is typically 'signed_cookie'
        # The API response structure varies, but often the signed URL is nested under 'media' or similar.
        signed_cookie_url = content_data.get('signed_cookie') 
        
        if not signed_cookie_url:
            logger.error("Signed cookie URL not found in API response.")
            raise ValueError("API response for content ID contains no 'signed_cookie' or similar URL.")

        # 3. Parse the URL to get only the query parameters
        # Example URL: https://media.adventuresinodyssey.com/.../*?Policy=...&Signature=...&Key-Pair-Id=...
        parsed_url = urlparse(signed_cookie_url)
        
        # The query component is the part after the '?'
        if not parsed_url.query:
            logger.error(f"URL contains no query parameters: {signed_cookie_url}")
            raise ValueError("The retrieved signed cookie URL did not contain a query string.")
            
        logger.info(f"Successfully extracted signed cookie query for ID: {content_id}")
        
        # *** MODIFICATION HERE ***
        # Prepend the '?' to the query string before returning.
        return '?' + parsed_url.query
        
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Performs an authenticated GET request to a generalized API endpoint.

        Args:
            endpoint: The relative API path (e.g., 'content/random').
            params: Optional dictionary of query parameters.
            headers: Optional dictionary of headers to override or add for this request.
            
        Returns:
            Dict[str, Any]: The parsed JSON response from the API.
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails after all retry attempts.
        """
        if not self.ensure_authenticated():
            raise RuntimeError(f"Cannot perform GET request to {endpoint}: Failed to authenticate user.")
            
        # Construct the full URL by prepending the base and the API prefix
        full_endpoint = f"{API_PREFIX}{endpoint}"
        url = f"{self.config['api_base']}{full_endpoint}"
        
        # --- HEADER OVERRIDE LOGIC ---
        # 1. Start with the session's default headers
        request_headers = self.session.headers.copy()
        # 2. Update/Override with the provided headers
        if headers:
            request_headers.update(headers)
        # -----------------------------

        def make_request():
            # Pass the custom headers to the request call
            response = self.session.get(url, params=params, headers=request_headers)
            return response

        try:
            logger.info(f"Attempting GET request to: {full_endpoint}")
            response = make_request()

            # Handle 401 Unauthorized
            if response.status_code == 401:
                logger.warning("GET request failed with 401 Unauthorized. Attempting re-authentication...")
                if self.ensure_authenticated():
                    logger.info("Re-authentication successful. Retrying request...")
                    # If re-auth succeeds, the session headers are updated, but we still need 
                    # to use the potentially overridden headers for the retry.
                    # Since session.headers updates 'Authorization', we re-copy it here.
                    request_headers = self.session.headers.copy()
                    if headers:
                        request_headers.update(headers)
                    response = make_request()
                else:
                    response.raise_for_status() 

            response.raise_for_status()
            logger.info(f"GET request successful for: {full_endpoint}")
            return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error(f"GET request failed for {full_endpoint}: {e}")
            raise

    def post(self, endpoint: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Performs an authenticated POST request to a generalized API endpoint with JSON data.
        
        Args:
            endpoint: The relative API path (e.g., 'contentgrouping/search').
            payload: The JSON dictionary to be sent in the request body.
            headers: Optional dictionary of headers to override or add for this request.
            
        Returns:
            Dict[str, Any]: The parsed JSON response from the API.
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails after all retry attempts.
        """
        if not self.ensure_authenticated():
            raise RuntimeError(f"Cannot perform POST request to {endpoint}: Failed to authenticate user.")
            
        # Construct the full URL by prepending the base and the API prefix
        full_endpoint = f"{API_PREFIX}{endpoint}"
        url = f"{self.config['api_base']}{full_endpoint}"
        
        # --- HEADER OVERRIDE LOGIC ---
        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)
        # -----------------------------

        def make_request():
            # Pass the custom headers to the request call
            # Use json=payload to automatically set Content-Type: application/json
            response = self.session.post(url, json=payload, headers=request_headers)
            return response

        try:
            logger.info(f"Attempting POST request to: {full_endpoint}")
            response = make_request()

            # Handle 401 Unauthorized
            if response.status_code == 401:
                logger.warning("POST request failed with 401 Unauthorized. Attempting re-authentication...")
                if self.ensure_authenticated():
                    logger.info("Re-authentication successful. Retrying request...")
                    # Update request headers after re-authentication
                    request_headers = self.session.headers.copy()
                    if headers:
                        request_headers.update(headers)
                    response = make_request()
                else:
                    response.raise_for_status() 

            response.raise_for_status()
            logger.info(f"POST request successful for: {full_endpoint}")
            return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error(f"POST request failed for {full_endpoint}: {e}")
            raise

    def put(self, endpoint: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Performs an authenticated PUT request to a generalized API endpoint with JSON data.
        
        Args:
            endpoint: The relative API path (e.g., 'content').
            payload: The JSON dictionary to be sent in the request body.
            headers: Optional dictionary of headers to override or add for this request.
            
        Returns:
            Dict[str, Any]: The parsed JSON response from the API, or a success dictionary if no content is returned.
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails after all retry attempts.
        """
        if not self.ensure_authenticated():
            raise RuntimeError(f"Cannot perform PUT request to {endpoint}: Failed to authenticate user.")
            
        # Construct the full URL by prepending the base and the API prefix
        full_endpoint = f"{API_PREFIX}{endpoint}"
        url = f"{self.config['api_base']}{full_endpoint}"
        
        # --- HEADER OVERRIDE LOGIC ---
        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)
        # -----------------------------

        def make_request():
            # Pass the custom headers to the request call
            # Use json=payload to automatically set Content-Type: application/json
            response = self.session.put(url, json=payload, headers=request_headers)
            return response

        try:
            logger.info(f"Attempting PUT request to: {full_endpoint}")
            response = make_request()

            # Handle 401 Unauthorized
            if response.status_code == 401:
                logger.warning("PUT request failed with 401 Unauthorized. Attempting re-authentication...")
                if self.ensure_authenticated():
                    logger.info("Re-authentication successful. Retrying request...")
                    # Update request headers after re-authentication
                    request_headers = self.session.headers.copy()
                    if headers:
                        request_headers.update(headers)
                    response = make_request()
                else:
                    response.raise_for_status() 

            response.raise_for_status()
            logger.info(f"PUT request successful for: {full_endpoint}")
            # API might return no content for PUT (204 No Content), so check for content before parsing
            return response.json() if response.content else {"status": "success"}

        except requests.exceptions.HTTPError as e:
            logger.error(f"PUT request failed for {full_endpoint}: {e}")
            raise
        
    def delete(self, endpoint: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Performs an authenticated DELETE request to a generalized API endpoint.

        Args:
            endpoint: The relative API path (e.g., 'content/123').
            params: Optional dictionary of query parameters.
            headers: Optional dictionary of headers to override or add for this request.
            
        Returns:
            Dict[str, Any]: The parsed JSON response from the API.
            
        Raises:
            requests.exceptions.HTTPError: If the API request fails after all retry attempts.
        """
        if not self.ensure_authenticated():
            raise RuntimeError(f"Cannot perform DELETE request to {endpoint}: Failed to authenticate user.")
            
        # Construct the full URL by prepending the base and the API prefix
        full_endpoint = f"{API_PREFIX}{endpoint}"
        url = f"{self.config['api_base']}{full_endpoint}"
        
        # --- HEADER OVERRIDE LOGIC ---
        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)
        # -----------------------------

        def make_request():
            # Use the delete method of the session
            response = self.session.delete(url, params=params, headers=request_headers)
            return response

        try:
            logger.info(f"Attempting DELETE request to: {full_endpoint}")
            response = make_request()

            # Handle 401 Unauthorized
            if response.status_code == 401:
                logger.warning("DELETE request failed with 401 Unauthorized. Attempting re-authentication...")
                if self.ensure_authenticated():
                    logger.info("Re-authentication successful. Retrying request...")
                    
                    # Refresh headers with the new session token, then re-apply overrides
                    request_headers = self.session.headers.copy()
                    if headers:
                        request_headers.update(headers)
                    response = make_request()
                else:
                    response.raise_for_status() 

            response.raise_for_status()
            logger.info(f"DELETE request successful for: {full_endpoint}")
            
            return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error(f"DELETE request failed for {full_endpoint}: {e}")
            raise